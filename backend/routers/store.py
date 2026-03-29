from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import subprocess
import os

from backend.database import get_db, InstalledApp, Service
from backend.routers.auth import get_current_user, User
from sqlalchemy.orm import Session

router = APIRouter()

APP_REGISTRY = {
    "nginx": {
        "name": "Nginx Web Server",
        "command": "apt update && apt install nginx -y",
        "description": "High performance edge web server.",
        "service_config": {"command": "nginx", "port": 80}
    },
    "php": {
        "name": "PHP-FPM",
        "command": "apt update && apt install php-fpm php-curl php-gd php-mysql -y",
        "description": "Popular general-purpose scripting language for web.",
        "service_config": {"command": "php-fpm", "port": None}
    },
    "filebrowser": {
        "name": "File Browser",
        "command": "curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash",
        "description": "Powerful web-based file manager.",
        "service_config": {"command": "filebrowser -p 8083", "port": 8083}
    },
    "aria2": {
        "name": "Aria2 Downloader",
        "command": "apt update && apt install aria2 -y",
        "description": "Lightweight multi-protocol download utility.",
        "service_config": {"command": "aria2c --enable-rpc --rpc-listen-all", "port": 6800}
    },
    "transmission": {
        "name": "Transmission",
        "command": "apt update && apt install transmission-daemon -y",
        "description": "Fast and easy BitTorrent client with web interface.",
        "service_config": {"command": "transmission-daemon -f", "port": 9091}
    },
    "adguard": {
        "name": "AdGuard Home",
        "command": "curl -s -S -L https://raw.githubusercontent.com/AdguardTeam/AdGuardHome/master/scripts/install.sh | sh -s -- -v",
        "description": "Network-wide ads & trackers blocking with a beautiful UI.",
        "service_config": {"command": "/opt/AdGuardHome/AdGuardHome", "port": 3000}
    },
    "mariadb": {
        "name": "MariaDB (MySQL)",
        "command": "apt update && apt install mariadb-server -y",
        "description": "Community-developed relational database management system.",
        "service_config": {"command": "mysqld", "port": 3306}
    },
    "redis": {
        "name": "Redis",
        "command": "apt update && apt install redis-server -y",
        "description": "In-memory data structure store, used as database and cache.",
        "service_config": {"command": "redis-server", "port": 6379}
    },
    "gitea": {
        "name": "Gitea",
        "command": "apt update && apt install gitea -y",
        "description": "A painless self-hosted Git service (Alternative to GitHub).",
        "service_config": {"command": "gitea web", "port": 3000}
    }
}

class AppResponse(BaseModel):
    key: str
    name: str
    description: str
    installed: bool

@router.get("/", response_model=list[AppResponse])
def list_apps(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    apps = []
    installed_db = db.query(InstalledApp).all()
    installed_keys = [app.app_key for app in installed_db]
    
    for key, info in APP_REGISTRY.items():
        # A real system would check if binary exists (e.g. `which nginx`)
        apps.append(AppResponse(
            key=key, 
            name=info["name"], 
            description=info["description"], 
            installed=key in installed_keys
        ))
    return apps

def run_install(app_key: str, command: str, db: Session, service_config: dict | None = None):
    try:
        # Run in background. Output can be redirected to a log file.
        log_file = f"/tmp/panel_install_{app_key}.log"
        with open(log_file, "w") as f:
            f.write(f"Starting installation of {app_key}...\n")
            f.write(f"Command: {command}\n\n")
            
        process = subprocess.Popen(
            f"{command} >> {log_file} 2>&1", 
            shell=True
        )
        process.wait()
        
        if process.returncode == 0:
            # update DB
            installed = InstalledApp(app_key=app_key, status="installed")
            db.add(installed)
            
            if service_config:
                app_name = APP_REGISTRY[app_key]["name"]
                existing = db.query(Service).filter(Service.name == app_name).first()
                if not existing:
                    new_svc = Service(
                        name=app_name,
                        command=service_config["command"],
                        port=service_config.get("port"),
                        autostart=False,
                        log_file=f"/tmp/service_{app_key}.log"
                    )
                    db.add(new_svc)
            db.commit()
        else:
             with open(log_file, "a") as f:
                 f.write(f"\nInstallation failed with exit code: {process.returncode}\n")
    except Exception as e:
         with open(log_file, "a") as f:
            f.write(f"Installation failed: {str(e)}\n")

@router.post("/{app_key}/install")
def install_app(app_key: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if app_key not in APP_REGISTRY:
        raise HTTPException(status_code=404, detail="App not found in registry")
        
    app_info = APP_REGISTRY[app_key]
    background_tasks.add_task(run_install, app_key, app_info["command"], db, app_info.get("service_config"))
    
    return {"message": f"Installation of {app_info['name']} started in background.", "log_file": f"/tmp/panel_install_{app_key}.log"}
