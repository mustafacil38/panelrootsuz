# VERSION: 3.0 - ULTRA ROBUST - NO DB DEPENDENCY
import subprocess
import os
import re
import time
import threading
import psutil
import logging

# Set up logging for background errors
logging.basicConfig(filename='panel_error.log', level=logging.ERROR)

# Global storage for background metrics
_metrics = {
    "cpu": 0.0,
    "net_io": {"sent": 0, "recv": 0, "time": 0, "up": 0, "down": 0}
}

def get_net_usage_manual():
    """Manually parse /proc/net/dev for PRoot/Termux environments."""
    try:
        if os.path.exists("/proc/net/dev"):
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()
            t_recv = 0
            t_sent = 0
            for line in lines[2:]: 
                parts = line.split()
                if len(parts) > 9:
                    t_recv += int(parts[1])
                    t_sent += int(parts[9])
            return t_sent, t_recv
    except Exception as e:
        logging.error(f"Network manual error: {e}")
    return None, None

def get_core_count():
    """Detect number of CPU cores from /proc/stat."""
    try:
        if os.path.exists("/proc/stat"):
            with open("/proc/stat", "r") as f:
                return len([line for line in f if line.startswith("cpu") and line[3].isdigit()])
    except: pass
    return 1

def _get_cpu_usage_top():
    """Fallback: Parse 'top' output with multi-core support."""
    try:
        cores = get_core_count()
        output = subprocess.check_output(["top", "-bn1"], stderr=subprocess.STDOUT, timeout=1).decode()
        for line in output.split('\n'):
            if "CPU:" in line or "%Cpu(s):" in line:
                parts = line.replace('%', ' ').replace(',', '.').split()
                for i, p in enumerate(parts):
                    if p.lower() in ["idle", "id"]:
                        idle_val = float(parts[i-1])
                        if idle_val > 100 and cores > 1:
                            idle_val = idle_val / cores
                        return round(100.0 - idle_val, 1)
    except Exception as e:
        logging.error(f"Top CPU error: {e}")
    return None

def _get_cpu_times():
    """Manually parse /proc/stat to get total and idle CPU times."""
    try:
        if os.access("/proc/stat", os.R_OK):
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("cpu "):
                        parts = [float(p) for p in line.split()[1:]]
                        return sum(parts), parts[3]
    except Exception as e:
        logging.error(f"Proc stat error: {e}")
    return None, None

def _bg_metric_updater():
    """Background task to poll metrics non-blockingly."""
    prev_total, prev_idle = _get_cpu_times()
    
    while True:
        try:
            # CPU Metrics logic
            curr_total, curr_idle = _get_cpu_times()
            
            if curr_total is not None and prev_total is not None:
                diff_total = curr_total - prev_total
                diff_idle = curr_idle - prev_idle
                
                if diff_total > 1: 
                    usage = 100 * (1.0 - (diff_idle / diff_total))
                    _metrics["cpu"] = round(max(0.0, min(100.0, usage)), 1)
                    prev_total, prev_idle = curr_total, curr_idle
                else:
                    top_val = _get_cpu_usage_top()
                    if top_val is not None:
                        _metrics["cpu"] = top_val
            else:
                top_val = _get_cpu_usage_top()
                if top_val is not None:
                    _metrics["cpu"] = top_val
                # Try to re-initialize prev values if they were None
                if prev_total is None:
                    prev_total, prev_idle = curr_total, curr_idle

            # Network IO logic
            curr_sent, curr_recv = get_net_usage_manual()
            if curr_sent is None:
                try:
                    net = psutil.net_io_counters()
                    curr_sent, curr_recv = net.bytes_sent, net.bytes_recv
                except: curr_sent, curr_recv = 0, 0
                
            now = time.time()
            if _metrics["net_io"]["time"] > 0:
                dt = now - _metrics["net_io"]["time"]
                if dt > 0:
                    _metrics["net_io"]["up"] = max(0, (curr_sent - _metrics["net_io"]["sent"]) / dt)
                    _metrics["net_io"]["down"] = max(0, (curr_recv - _metrics["net_io"]["recv"]) / dt)
            
            _metrics["net_io"]["sent"] = curr_sent
            _metrics["net_io"]["recv"] = curr_recv
            _metrics["net_io"]["time"] = now
                
        except Exception as e:
            logging.error(f"BG Thread major error: {e}")
        
        time.sleep(1)

# Start background thread automatically
threading.Thread(target=_bg_metric_updater, daemon=True).start()

def get_cpu_info():
    return {"percent": _metrics["cpu"]}

def get_ram_info():
    try:
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
            "percent": mem.percent
        }
    except Exception as e:
        return {"total": 0, "used": 0, "free": 0, "percent": 0}

def get_disk_info(path="/"):
    try:
        usage = psutil.disk_usage(path)
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent
        }
    except Exception as e:
        return {"total": 0, "used": 0, "free": 0, "percent": 0}

def get_net_info():
    return {
        "bytes_sent": _metrics["net_io"]["sent"],
        "bytes_recv": _metrics["net_io"]["recv"],
        "up_speed": _metrics["net_io"]["up"],
        "down_speed": _metrics["net_io"]["down"]
    }

def get_os_info():
    info = {
        "hostname": "Unknown",
        "kernel": "Unknown",
        "os_type": "Unknown",
        "uptime": "Unknown",
        "cpu_model": "Unknown"
    }
    try:
        info["hostname"] = os.uname().nodename
        info["kernel"] = os.uname().release
        info["os_type"] = os.uname().sysname
    except: pass
    try:
        # Standard fallback for Termux/Android
        if info["hostname"] == "Unknown":
            import socket
            info["hostname"] = socket.gethostname()
    except: pass

    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            info["uptime"] = f"{hours}h {minutes}m"
    except: pass
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        info["cpu_model"] = line.split(":")[1].strip()
                        break
    except: pass
    return info

def get_all_system_info():
    return {
        "cpu": get_cpu_info(),
        "ram": get_ram_info(),
        "disk": get_disk_info(),
        "net": get_net_info(),
        "os": get_os_info()
    }
