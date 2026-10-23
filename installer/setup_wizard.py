import os
import sys
import shutil
import threading
import time
from pathlib import Path

# Ensure root directory and PyInstaller bundle directory are in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

meipass = getattr(sys, "_MEIPASS", None)
if meipass and meipass not in sys.path:
    sys.path.insert(0, meipass)

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from installer.registry import (
        register_open_with,
        register_uninstall_entry,
        create_shortcut,
        unregister_all
    )
except ImportError:
    from registry import (
        register_open_with,
        register_uninstall_entry,
        create_shortcut,
        unregister_all
    )

try:
    from gui.window_utils import apply_titlebar_styling
except ImportError:
    def apply_titlebar_styling(window, is_dark: bool = True):
        pass

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

def get_default_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / "SizeWiz"
    return Path.home() / "AppData" / "Local" / "Programs" / "SizeWiz"

def get_start_menu_path() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SizeWiz.lnk"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SizeWiz.lnk"

def get_desktop_shortcut_path() -> Path:
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        # Check Desktop or OneDrive\Desktop
        desktop = Path(user_profile) / "Desktop"
        if desktop.exists():
            return desktop / "SizeWiz.lnk"
        onedrive_desktop = Path(user_profile) / "OneDrive" / "Desktop"
        if onedrive_desktop.exists():
            return onedrive_desktop / "SizeWiz.lnk"
    return Path.home() / "Desktop" / "SizeWiz.lnk"


class SetupWizard(ctk.CTk):
    def __init__(self, source_dir: Path):
        super().__init__()
        self.source_dir = source_dir

        self.title("")
        self.geometry("420x480")
        self.resizable(False, False)
        self._center_window(420, 480)
        self.after(50, self._apply_dwm)

        self._build_ui()

    def _center_window(self, width: int, height: int):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _apply_dwm(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        apply_titlebar_styling(self, is_dark=is_dark)

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # 1. BOTTOM-DOCKING: Pack bottom elements first to guarantee visibility
        self.status_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray",
            height=16
        )
        self.status_label.pack(side="bottom", fill="x", pady=(2, 0))

        self.install_btn = ctk.CTkButton(
            container,
            text="Install SizeWiz",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._on_install
        )
        self.install_btn.pack(side="bottom", fill="x", pady=(8, 0))

        # Progress bar (hidden initially, packed above button during install)
        self.progress_bar = ctk.CTkProgressBar(container, height=6)
        self.progress_bar.set(0)

        # 2. TOP-DOCKING: Header, path selector, options
        self.title_label = ctk.CTkLabel(
            container,
            text="SizeWiz Setup",
            font=ctk.CTkFont(family="Segoe UI Variable Display", size=20, weight="bold")
        )
        self.title_label.pack(side="top", pady=(0, 2))

        self.subtitle_label = ctk.CTkLabel(
            container,
            text="Smart Image Resizer for Windows",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        self.subtitle_label.pack(side="top", pady=(0, 12))

        # Install Path Section
        path_label = ctk.CTkLabel(
            container,
            text="Install Location",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w"
        )
        path_label.pack(side="top", fill="x", pady=(0, 2))

        path_frame = ctk.CTkFrame(container, fg_color="transparent")
        path_frame.pack(side="top", fill="x", pady=(0, 12))

        self.path_entry = ctk.CTkEntry(
            path_frame,
            height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.path_entry.insert(0, str(get_default_install_dir()))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse...",
            width=75,
            height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._on_browse
        )
        browse_btn.pack(side="right")

        # Options Section
        opts_label = ctk.CTkLabel(
            container,
            text="Integration Options",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w"
        )
        opts_label.pack(side="top", fill="x", pady=(0, 2))

        self.open_with_var = ctk.BooleanVar(value=True)
        self.start_menu_var = ctk.BooleanVar(value=True)
        self.desktop_var = ctk.BooleanVar(value=True)

        self.cb_open_with = ctk.CTkCheckBox(
            container,
            text="Register in Windows \"Open with\" menu",
            variable=self.open_with_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.cb_open_with.pack(side="top", anchor="w", pady=(0, 6))

        self.cb_start_menu = ctk.CTkCheckBox(
            container,
            text="Create Start Menu shortcut",
            variable=self.start_menu_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.cb_start_menu.pack(side="top", anchor="w", pady=(0, 6))

        self.cb_desktop = ctk.CTkCheckBox(
            container,
            text="Create Desktop shortcut",
            variable=self.desktop_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.cb_desktop.pack(side="top", anchor="w", pady=(0, 6))

    def _on_browse(self):
        chosen = filedialog.askdirectory(initialdir=self.path_entry.get().strip())
        if chosen:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, str(Path(chosen) / "SizeWiz"))

    def _on_install(self):
        target_dir = Path(self.path_entry.get().strip()).resolve()
        self.install_btn.configure(state="disabled", text="Installing...")
        self.progress_bar.pack(side="bottom", fill="x", pady=(0, 6))
        self.progress_bar.start()

        threading.Thread(
            target=self._install_worker,
            args=(target_dir,),
            daemon=True
        ).start()

    def _install_worker(self, target_dir: Path):
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_exe = target_dir / "SizeWiz.exe"

            # If re-installing, ensure any previous running SizeWiz instance is closed so files can be overwritten cleanly
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "SizeWiz.exe"], capture_output=True)
                time.sleep(0.2)
            except Exception:
                pass

            # Check for fast pre-extracted payload zip (zero temp decompression on subsequent runs)
            meipass = getattr(sys, "_MEIPASS", None)
            base_search = Path(meipass) if meipass else self.source_dir
            payload_zip = base_search / "sizewiz_payload.zip"

            if payload_zip.exists():
                import zipfile
                with zipfile.ZipFile(payload_zip, "r") as zf:
                    zf.extractall(target_dir)
            elif (base_search / "SizeWiz.exe").exists():
                shutil.copy2(base_search / "SizeWiz.exe", target_exe)
            else:
                # Fallback in development environment: copy all source files
                for item in self.source_dir.iterdir():
                    if item.name in (".git", ".gemini", "tests", "dist", "build", "__pycache__"):
                        continue
                    dest = target_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    elif item.is_file():
                        shutil.copy2(item, dest)

            # Register Open With
            if self.open_with_var.get():
                register_open_with(target_exe)

            # Register Uninstall Entry
            register_uninstall_entry(target_dir, target_exe)

            # Create Start Menu Shortcut
            if self.start_menu_var.get():
                sm_path = get_start_menu_path()
                sm_path.parent.mkdir(parents=True, exist_ok=True)
                create_shortcut(target_exe, sm_path, "SizeWiz Image Resizer")

            # Create Desktop Shortcut
            if self.desktop_var.get():
                dt_path = get_desktop_shortcut_path()
                create_shortcut(target_exe, dt_path, "SizeWiz Image Resizer")

            time.sleep(0.4)
            self.after(0, lambda: self._on_install_success(target_exe))

        except Exception as e:
            self.after(0, lambda: self._on_install_error(str(e)))

    def _on_install_success(self, target_exe: Path):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.title_label.configure(text="SizeWiz Installed!")
        self.subtitle_label.configure(text="Ready to use via right-click 'Open with'")
        self.status_label.configure(text="Successfully installed", text_color="#2ecc71")

        self.install_btn.configure(
            state="normal",
            text="Finish",
            command=self.destroy
        )

    def _on_install_error(self, err_msg: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text=f"Error: {err_msg}", text_color="#e74c3c")
        self.install_btn.configure(state="normal", text="Retry")


def run_setup(source_dir: Optional[Path] = None):
    if source_dir is None:
        if getattr(sys, "frozen", False):
            source_dir = Path(sys.executable).parent
        else:
            source_dir = Path(__file__).resolve().parent.parent

    app = SetupWizard(source_dir)
    app.mainloop()

if __name__ == "__main__":
    run_setup()
