import socket
import json
import threading
from typing import List, Callable, Optional

DEFAULT_PORT = 49281

def send_files_to_running_instance(files: List[str], port: int = DEFAULT_PORT) -> bool:
    """
    Attempts to send files to an already-running SizeWiz instance.
    Returns True if successfully handed off, False if no instance is listening.
    """
    if not files:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            payload = json.dumps({"action": "add_files", "files": files}).encode("utf-8")
            s.sendall(payload)
            # Wait for quick ack
            data = s.recv(1024)
            return data == b"OK"
    except Exception:
        return False


class IPCServer:
    """
    Background socket listener for the primary SizeWiz instance.
    Receives incoming file lists forwarded from Windows Explorer and dispatches to GUI.
    """
    def __init__(self, callback: Callable[[List[str]], None], port: int = DEFAULT_PORT):
        self.callback = callback
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("127.0.0.1", self.port))
            self.server_socket.listen(5)
            self.is_running = True

            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            return True
        except Exception:
            return False

    def _listen_loop(self):
        while self.is_running:
            try:
                client_sock, _ = self.server_socket.accept()
                with client_sock:
                    client_sock.settimeout(1.0)
                    data = client_sock.recv(65536)
                    if data:
                        try:
                            msg = json.loads(data.decode("utf-8"))
                            if msg.get("action") == "add_files":
                                files = msg.get("files", [])
                                if files and self.callback:
                                    self.callback(files)
                                client_sock.sendall(b"OK")
                        except Exception:
                            pass
            except Exception:
                break

    def stop(self):
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
