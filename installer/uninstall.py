import os
import sys
import subprocess
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk

from installer.registry import unregister_all
from installer.setup_wizard import get_start_menu_path, get_desktop_shortcut_path

def perform_uninstall(install_dir: Path):
    root = ctk.CTk()
    root.withdraw()

    confirm = messagebox.askyesno(
        "Uninstall SizeWiz",
        "Are you sure you want to completely uninstall SizeWiz?",
        icon="question"
    )
    if not confirm:
        root.destroy()
        sys.exit(0)

    try:
        # 1. Clean registry entries
        unregister_all()

        # 2. Delete Start Menu shortcut
        sm_path = get_start_menu_path()
        if sm_path.exists():
            try:
                sm_path.unlink()
            except Exception:
                pass

        # 3. Delete Desktop shortcut
        dt_path = get_desktop_shortcut_path()
        if dt_path.exists():
            try:
                dt_path.unlink()
            except Exception:
                pass

        # 4. Schedule directory removal after process exits
        cmd = f'cmd.exe /c timeout /t 1 /nobreak >nul & rd /s /q "{str(install_dir)}"'
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

        messagebox.showinfo("SizeWiz", "SizeWiz has been uninstalled successfully.")
    except Exception as e:
        messagebox.showerror("SizeWiz", f"Error during uninstallation: {e}")
    finally:
        root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).parent
    else:
        app_dir = Path(__file__).resolve().parent.parent
    perform_uninstall(app_dir)
