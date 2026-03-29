import os
import pty
import subprocess
import select
import asyncio
from fastapi import WebSocket

class TerminalSession:
    def __init__(self, command: str, websocket: WebSocket):
        self.command = command
        self.websocket = websocket
        self.fd = None
        self.pid = None

    async def run(self):
        self.pid, self.fd = pty.fork()
        
        if self.pid == 0:  # Child process
            # Set some env vars for better terminal experience
            os.environ["TERM"] = "xterm-256color"
            os.execlp("sh", "sh", "-c", self.command)
        
        # Parent process: bridge between PTY and WebSocket
        try:
            while True:
                # Non-blocking check for PTY output
                timeout = 0.02
                r, _, _ = select.select([self.fd], [], [], timeout)
                if r:
                    data = os.read(self.fd, 4096)
                    if not data:
                        break
                    await self.websocket.send_text(data.decode(errors='ignore'))
                
                # Small sleep to yield to other tasks
                await asyncio.sleep(0.01)
                
                # Check if process is still alive
                pid, status = os.waitpid(self.pid, os.WNOHANG)
                if pid != 0:
                    await self.websocket.send_text("\r\n[Process completed]\r\n")
                    break
                    
        except Exception as e:
            await self.websocket.send_text(f"\r\n[Terminal Error: {str(e)}]\r\n")
        finally:
            if self.fd:
                os.close(self.fd)
