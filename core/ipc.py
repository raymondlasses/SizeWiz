import socket
import json
import threading
import time
import os
import sys
from typing import List, Callable, Optional, Tuple

DEFAULT_PORT = 49281
MUTEX_NAME = "Local\\SizeWiz_SingleInstance_Mutex"

def acquire_single_instance_mutex(mutex_name: str = MUTEX_NAME) -> Tuple[Optional[int], bool]:
    """
    Attempts to create/acquire a named Windows mutex.
    Returns (handle, is_primary).
    If running on Windows and mutex already exists, is_primary is False.
    """
    if sys.platform != "win32":
        # Non-Windows fallback (e.g. Linux CI/test environments)
        return None, True

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183

        handle = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        is_primary = (last_error != ERROR_ALREADY_EXISTS) and (handle != 0)
        return handle, is_primary
    except Exception:
        return None, True


def send_files_to_running_instance(files: List[str], port: int = DEFAULT_PORT) -> bool:
    """
    Attempts to send files (or focus signal) to an already-running SizeWiz instance.
    Returns True if successfully handed off, False if no instance is listening.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            if files:
                payload = json.dumps({"action": "add_files", "files": files}).encode("utf-8")
            else:
                payload = json.dumps({"action": "focus"}).encode("utf-8")
            s.sendall(payload)
            # Wait for quick ack
            data = s.recv(1024)
            return data == b"OK"
    except Exception:
        return False


def send_files_with_retry(files: List[str], port: int = DEFAULT_PORT, max_attempts: int = 40, delay: float = 0.05) -> bool:
    """
    Retries sending files to the primary instance up to max_attempts times.
    Designed for secondary instances launched simultaneously by Windows Explorer.
    """
    for _ in range(max_attempts):
        if send_files_to_running_instance(files, port):
            return True
        time.sleep(delay)
    return False


class IPCServer:
    """
    Background socket listener for the primary SizeWiz instance.
    Receives incoming file lists forwarded from Windows Explorer and dispatches to GUI.
    """
    def __init__(
        self,
        callback: Optional[Callable[[List[str]], None]] = None,
        focus_callback: Optional[Callable[[], None]] = None,
        port: int = DEFAULT_PORT
    ):
        self.callback = callback
        self.focus_callback = focus_callback
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.pending_files: List[str] = []
        self.lock = threading.Lock()

    def start(self) -> bool:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("127.0.0.1", self.port))
            self.server_socket.listen(10)
            self.is_running = True

            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            return True
        except Exception:
            return False

    def set_callback(self, callback: Callable[[List[str]], None]):
        """Sets the file arrival callback and flushes any pending files received during startup."""
        self.callback = callback
        with self.lock:
            flushed = list(self.pending_files)
            self.pending_files.clear()
        if flushed and self.callback:
            self.callback(flushed)

    def set_focus_callback(self, focus_callback: Callable[[], None]):
        self.focus_callback = focus_callback

    def get_and_clear_pending_files(self) -> List[str]:
        """Returns all accumulated files received before GUI initialization."""
        with self.lock:
            flushed = list(self.pending_files)
            self.pending_files.clear()
        return flushed

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
                            action = msg.get("action")
                            if action == "add_files":
                                files = msg.get("files", [])
                                if files:
                                    if self.callback:
                                        self.callback(files)
                                    else:
                                        with self.lock:
                                            self.pending_files.extend(files)
                                if self.focus_callback:
                                    self.focus_callback()
                            elif action == "focus":
                                if self.focus_callback:
                                    self.focus_callback()

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
