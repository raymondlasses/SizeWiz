import sys
import os
from pathlib import Path
from core.ipc import send_files_to_running_instance, IPCServer
from gui.app import SizeWizApp

def main():
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

    # Check if another SizeWiz instance is already open
    if incoming_files and send_files_to_running_instance(incoming_files):
        # Successfully forwarded files to running window; exit secondary process
        sys.exit(0)

    # Launch primary application instance
    app = SizeWizApp(initial_files=incoming_files)

    # Start IPC server to accept any concurrent launches from Windows Explorer
    ipc_server = IPCServer(callback=app.add_files_from_external)
    ipc_server.start()

    try:
        app.mainloop()
    finally:
        ipc_server.stop()

if __name__ == "__main__":
    main()
