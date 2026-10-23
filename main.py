import sys
import os
import time
from pathlib import Path
from core.ipc import (
    acquire_single_instance_mutex,
    send_files_with_retry,
    IPCServer
)

# Keep mutex handle alive at module scope for process lifetime
_mutex_handle = None

def main():
    global _mutex_handle

    # Handle uninstall flag from Windows Add/Remove programs
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        from installer.uninstall import perform_uninstall
        if getattr(sys, "frozen", False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).resolve().parent
        perform_uninstall(app_dir)
        return

    # Collect any image files passed as arguments
    incoming_files = [arg for arg in sys.argv[1:] if os.path.exists(arg)]

    # Acquire named Windows mutex to guarantee single-instance enforcement
    _mutex_handle, is_primary = acquire_single_instance_mutex()

    if not is_primary:
        # SECONDARY INSTANCE:
        # Another SizeWiz instance is already running or being launched by Windows Explorer.
        # Retry sending files (or focus trigger) to the primary instance, then exit cleanly.
        send_files_with_retry(incoming_files)
        sys.exit(0)

    # PRIMARY INSTANCE:
    # Start IPC server IMMEDIATELY (< 2ms) to catch any concurrent launches from Windows Explorer
    ipc_server = IPCServer()
    ipc_server.start()

    # Small 120ms aggregation window to catch near-simultaneous Explorer processes
    if incoming_files:
        time.sleep(0.12)

    all_initial_files = list(incoming_files) + ipc_server.get_and_clear_pending_files()

    # Launch GUI application
    from gui.app import SizeWizApp
    app = SizeWizApp(initial_files=all_initial_files)

    # Hook live callbacks for any future Explorer launches
    ipc_server.set_callback(app.add_files_from_external)
    ipc_server.set_focus_callback(app.bring_to_front)

    try:
        app.mainloop()
    finally:
        ipc_server.stop()

if __name__ == "__main__":
    main()
