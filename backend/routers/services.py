from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import subprocess
import os
import psutil
import shutil
import glob
import re

from backend.database import get_db, Service
from backend.routers.auth import get_current_user, User

router = APIRouter()

class ServiceCreate(BaseModel):
    name: str
    command: str
    port: int | None = None
    autostart: bool = False
    log_file: str | None = None
    config_file: str | None = None

class ServiceOut(BaseModel):
    id: int
    name: str
    command: str
    port: int | None
    autostart: bool
    log_file: str | None
    config_file: str | None
    status: str # running, stopped
    
    class Config:
        from_attributes = True

def is_service_running(command: str):
    """Check if a service is running by name or command using robust detection."""
    try:
        # Resolve names via psutil + ps -ax fallbacks
        running_names = get_running_process_names()
        # Extract binary name from potential full command path
        base_cmd = command.split()[0].split('/')[-1].lower()
        return any(base_cmd in r_name for r_name in running_names)
    except Exception:
        return False


def find_config(daemon_name: str) -> str | None:
    found = []
    if "nginx" in daemon_name:
        paths = ["/etc/nginx/nginx.conf", "/data/data/com.termux/files/usr/etc/nginx/nginx.conf",
                 "/etc/nginx/sites-enabled/default", "/data/data/com.termux/files/usr/etc/nginx/sites-enabled/default",
                 "/etc/nginx/conf.d/default.conf"]
    elif "php" in daemon_name:
        paths = ["/etc/php/php.ini", "/data/data/com.termux/files/usr/etc/php.ini"]
        # Broaden search for various PHP versions and extra config files
        for v in ["8.4", "8.3", "8.2", "8.1", "8.0", "7.4"]:
            paths.append(f"/etc/php/{v}/fpm/php.ini")
            paths.append(f"/etc/php/{v}/fpm/php-fpm.conf")
            paths.append(f"/etc/php/{v}/fpm/pool.d/www.conf")
            paths.append(f"/etc/php/{v}/cli/php.ini")
    elif "mysql" in daemon_name or "mariadb" in daemon_name:
        paths = ["/etc/mysql/my.cnf", "/data/data/com.termux/files/usr/etc/my.cnf"]
    else:
        paths = []
        
    for p in paths:
        if os.path.exists(p):
            found.append(p)
    return ",".join(found) if found else None

def get_running_process_names():
    """Robustly get names of all running processes using psutil and manual ps fallback."""
    names = set()
    # 1. psutil
    try:
        for p in psutil.process_iter(['name', 'cmdline']):
            if p.info['name']:
                names.add(p.info['name'].lower())
            if p.info['cmdline'] and len(p.info['cmdline']) > 0:
                # Add the base name of the first argument (path to binary)
                names.add(p.info['cmdline'][0].split('/')[-1].lower())
    except Exception:
        pass

    # 2. Manual ps -ax -o comm fallback (for PRoot environments)
    try:
        output = subprocess.check_output(["ps", "-ax", "-o", "comm"], stderr=subprocess.STDOUT).decode()
        for line in output.split('\n')[1:]: # Skip header
            if line.strip():
                # Some versions of ps output the full path, some just the command
                names.add(line.strip().split('/')[-1].lower())
    except Exception:
        pass
    
    return list(names)

def auto_discover_services(db: Session):
    """Detect installed and running services in Termux/Debian environment with strict matching."""
    # name -> {bin_prefix, display_name, port_hint, config_hint}
    # bin_prefix is what the binary MUST start with.
    known_daemons = {
        "nginx": {"prefix": "nginx", "name": "Nginx", "port": 80, "conf": "/etc/nginx/nginx.conf"},
        "php-fpm": {"prefix": "php-fpm", "name": "PHP-FPM", "port": None, "conf": "/etc/php/*/fpm/php-fpm.conf"},
        "mysql": {"prefix": "mysqld", "name": "MySQL", "port": 3306, "conf": "/etc/mysql/my.cnf"},
        "mariadb": {"prefix": "mariadbd", "name": "MariaDB", "port": 3306, "conf": "/etc/mysql/my.cnf"},
        "redis": {"prefix": "redis-server", "name": "Redis", "port": 6379, "conf": "/etc/redis/redis.conf"},
        "filebrowser": {"prefix": "filebrowser", "name": "File Browser", "port": 8083, "conf": ""},
        "transmission": {"prefix": "transmission-daemon", "name": "Transmission", "port": 9091, "conf": ""},
        "aria2": {"prefix": "aria2c", "name": "Aria2", "port": 6800, "conf": ""},
        "gitea": {"prefix": "gitea", "name": "Gitea", "port": 3000, "conf": ""}
    }

    # Binaries to EXPLICITLY ignore even if they match a prefix
    EXCLUSION_LIST = ["php-config", "phpize", "mysql_config", "mariadb_config", "redis-cli", "redis-benchmark"]
    
    # 1. CLEANUP: If there's a lot of junk, let's just wipe 'system' services that don't match the list
    # This keeps 'custom' services intact.
    # We only do this if the user hasn't explicitly protected them.
    # To keep it simple, we check for services that have very long names or look like junk.
    # But better: delete all 'system' type services once and rediscover.
    system_services = db.query(Service).filter(Service.type == "system").all()
    if len(system_services) > 15: # Indicator of discovery chaos
        for s in system_services:
            db.delete(s)
        db.commit()
    
    existing_records = db.query(Service).all()
    existing_commands = [s.command.lower() for s in existing_records]
    existing_names = [s.name.lower() for s in existing_records]
    
    # 2. Scavenge all binary files from system paths
    all_binaries = set()
    system_paths = ["/usr/sbin", "/usr/bin", "/bin", "/data/data/com.termux/files/usr/bin", "/data/data/com.termux/files/usr/sbin"]
    for path in system_paths:
        if os.path.exists(path):
            try:
                for entry in os.listdir(path):
                    if entry.lower() not in EXCLUSION_LIST:
                        all_binaries.add(entry.lower())
            except: continue
    
    found_any = False

    for key, info in known_daemons.items():
        prefix = info["prefix"]
        display_name_base = info["name"]
        
        # Look for matches: must start with prefix and be followed by nothing or a version (e.g. php-fpm8.2)
        # Regex: ^prefix([0-9\.]+)?$
        pattern = re.compile(f"^{re.escape(prefix)}([0-9\\.]+)?$")
        matches = [b for b in all_binaries if pattern.match(b)]
        
        for matched_bin in matches:
            if matched_bin.lower() in existing_commands:
                continue
                
            display_name = matched_bin.capitalize() if prefix != matched_bin else display_name_base
            if display_name.lower() in existing_names:
                 continue

            conf_path = info["conf"]
            if conf_path and "*" in conf_path:
                matches_conf = glob.glob(conf_path)
                conf_path = matches_conf[0] if matches_conf else ""
            
            new_service = Service(
                name=display_name,
                command=matched_bin,
                port=info.get("port"),
                autostart=False,
                type="system", # Mark as auto-discovered
                config_file=conf_path,
                log_file=f"/tmp/{matched_bin}.log"
            )
            db.add(new_service)
            existing_commands.append(matched_bin.lower())
            existing_names.append(display_name.lower())
            found_any = True
    
    if found_any:
        db.commit()
    return found_any
    
    if found_any:
        db.commit()
    return found_any


@router.get("/", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    auto_discover_services(db)
    
    services = db.query(Service).all()
    results = []
    for s in services:
        status = "running" if is_service_running(s.command) else "stopped"
        results.append(ServiceOut(
            id=s.id, name=s.name, command=s.command, 
            port=s.port, autostart=s.autostart, 
            log_file=s.log_file, config_file=s.config_file, status=status
        ))
    return results

@router.post("/", response_model=ServiceOut)
def create_service(svc: ServiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_svc = Service(**svc.dict())
    db.add(db_svc)
    db.commit()
    db.refresh(db_svc)
    status = "running" if is_service_running(db_svc.command) else "stopped"
    return ServiceOut(**db_svc.__dict__, status=status)

@router.post("/{service_id}/start")
def start_service(service_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if is_service_running(svc.command):
        return {"message": "Service is already running"}
        
    try:
        # Extremely basic way to launch in background on termux
        # nohup is standard in unix
        cmd = f"nohup {svc.command} > {svc.log_file or '/dev/null'} 2>&1 &"
        subprocess.Popen(cmd, shell=True)
        return {"message": "Service started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{service_id}/stop")
def stop_service(service_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
        
    try:
        # Find PIDs. Note: `pkill -f` is dangerous, we try to match exact command or similar.
        subprocess.Popen(f"pkill -f '{svc.command}'", shell=True)
        return {"message": "Stop command sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{service_id}/logs")
def get_service_logs(service_id: int, lines: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
         raise HTTPException(status_code=404, detail="Service not found")
    
    if not svc.log_file or not os.path.exists(svc.log_file):
         return {"logs": "No log file found or specified."}
         
    try:
        output = subprocess.check_output(["tail", "-n", str(lines), svc.log_file], universal_newlines=True)
        return {"logs": output}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

class ConfigData(BaseModel):
    content: str
    file: str | None = None

@router.get("/{service_id}/config")
def get_service_config(service_id: int, file: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc or not svc.config_file:
        raise HTTPException(status_code=404, detail="Config file not found or configured for this service")
        
    allowed_files = [p.strip() for p in svc.config_file.split(",")]
    target_file = file if file else allowed_files[0]
    
    if target_file not in allowed_files:
        raise HTTPException(status_code=403, detail="File path not allowed")
        
    if not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail="Config file not found on disk")
        
    try:
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"content": content, "path": target_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{service_id}/config")
def save_service_config(service_id: int, data: ConfigData, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc or not svc.config_file:
        raise HTTPException(status_code=404, detail="Config file not configured")
        
    allowed_files = [p.strip() for p in svc.config_file.split(",")]
    target_file = data.file if data.file else allowed_files[0]
    
    if target_file not in allowed_files:
        raise HTTPException(status_code=403, detail="File path not allowed")
        
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(data.content)
        return {"message": "Configuration saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    svc = db.query(Service).filter(Service.id == service_id).first()
    if not svc:
         raise HTTPException(status_code=404, detail="Service not found")
    db.delete(svc)
    db.commit()
    return {"message": "Service deleted"}
