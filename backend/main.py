from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
import subprocess
from sqlalchemy.orm import Session
from backend.terminal_handler import TerminalSession
from backend.routers.store import APP_REGISTRY
from backend.utils.system_info import _metrics

from backend.database import engine, init_db, get_db
from backend.routers import auth, system, services, store

app = FastAPI(title="Termux Server Panel", debug=True)

# CORS setup (since the frontend and backend might run together)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
@app.on_event("startup")
def on_startup():
    init_db()

# Include Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(system.router, prefix="/api/system", tags=["System Info"])
app.include_router(services.router, prefix="/api/services", tags=["Service Management"])
app.include_router(store.router, prefix="/api/store", tags=["App Store"])

# WebSocket Terminal for Interactive Installation
@app.websocket("/ws/install/{app_key}")
async def websocket_install_terminal(websocket: WebSocket, app_key: str):
    await websocket.accept()
    if app_key not in APP_REGISTRY:
        await websocket.send_text("App not found in registry.")
        await websocket.close()
        return
    
    app_info = APP_REGISTRY[app_key]
    command = app_info["command"]
    
    session = TerminalSession(command, websocket)
    
    # Run the session but also listen for input from websocket
    # Create two tasks: one for running the PTY and one for reading websocket
    tty_task = asyncio.create_task(session.run())
    
    try:
        while not tty_task.done():
            # Wait for user input from browser
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                # Write to PTY
                if session.fd:
                    os.write(session.fd, data.encode())
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"WS Terminal Error: {e}")
    finally:
        if not tty_task.done():
            tty_task.cancel()
        await websocket.close()

# General Shell Terminal
@app.websocket("/ws/terminal/shell")
async def websocket_shell_terminal(websocket: WebSocket):
    await websocket.accept()
    # Use the system's preferred shell or fall back to sh
    shell = os.environ.get("SHELL", "sh")
    session = TerminalSession(shell, websocket)
    tty_task = asyncio.create_task(session.run())
    try:
        while not tty_task.done():
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                if session.fd:
                    os.write(session.fd, data.encode())
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
    finally:
        if not tty_task.done():
            tty_task.cancel()
        await websocket.close()

# Diagnostics Endpoint
@app.get("/api/debug/info")
async def get_debug_info(db: Session = Depends(get_db), current_user = Depends(auth.get_current_user)):
    diag = {
        "proc_stat_readable": os.access("/proc/stat", os.R_OK),
        "proc_stat_content": "N/A",
        "ps_output": "N/A",
        "top_output": "N/A",
        "working_dir": os.getcwd(),
        "metrics_cache": _metrics
    }
    
    try:
        if diag["proc_stat_readable"]:
            with open("/proc/stat", "r") as f:
                diag["proc_stat_content"] = f.read(200)
    except: pass
    
    try:
        diag["ps_output"] = subprocess.check_output(["ps", "-ax", "-o", "comm"], stderr=subprocess.STDOUT).decode()[:500]
    except Exception as e: diag["ps_output"] = f"Error: {str(e)}"
    
    try:
        diag["top_output"] = subprocess.check_output(["top", "-bn1"], stderr=subprocess.STDOUT).decode()[:500]
    except Exception as e: diag["top_output"] = f"Error: {str(e)}"
    
    return diag

# Mount Frontend App
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if not os.path.exists(FRONTEND_DIR):
    os.makedirs(FRONTEND_DIR)

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
