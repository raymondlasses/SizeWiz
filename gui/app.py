import os
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional
import customtkinter as ctk
from tkinter import filedialog

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_TKDND = True
except ImportError:
    HAS_TKDND = False
    DND_FILES = None

from core.config import load_config, save_config
from core.resizer import process_image, SUPPORTED_EXTENSIONS
from gui.window_utils import apply_titlebar_styling

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

WINDOW_WIDTH = 340
WINDOW_HEIGHT = 320


class SizeWizApp(ctk.CTk, TkinterDnD.DnDWrapper if HAS_TKDND else object):
    def __init__(self, initial_files: Optional[List[str]] = None):
        super().__init__()

        # Initialize TkinterDnD OLE subsystem
        self.has_dnd = False
        if HAS_TKDND:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.has_dnd = True
            except Exception:
                self.has_dnd = False

        self.files: List[Path] = []
        if initial_files:
            self._filter_and_add_files(initial_files)

        self.config = load_config()

        # Window Setup - identical fixed size for both drop and resize screens
        self.title("")  # Clean title bar without text
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self._center_window(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Title bar blending
        self.after(50, self._apply_dwm)

        # Root container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=(10, 12))

        # Enable native OLE drag and drop
        if self.has_dnd:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<DropEnter>>", self._on_dnd_enter)
                self.dnd_bind("<<DropLeave>>", self._on_dnd_leave)
                self.dnd_bind("<<Drop>>", self._on_dnd_drop)
            except Exception:
                pass

        if not self.files:
            # Standalone launch with 0 files: show drop zone UI
            self._build_drop_ui()
        else:
            # Right-click "Open with" launch with files: show main resize UI directly
            self._build_main_ui()

    def _center_window(self, width: int, height: int):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _apply_dwm(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        apply_titlebar_styling(self, is_dark=is_dark)

    def _filter_and_add_files(self, paths: List[str]):
        for p in paths:
            path = Path(p).resolve()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                if path not in self.files:
                    self.files.append(path)

    def _on_dnd_enter(self, event):
        """Visual feedback: only blue border/background highlight, text remains unchanged."""
        if hasattr(self, "drop_frame") and self.drop_frame.winfo_exists():
            self.drop_frame.configure(
                border_color="#3b8ed0",
                border_width=3,
                fg_color=("#e8f4fc", "#1c2a38")
            )
        elif hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(
                text="Drop to add image(s) to queue",
                text_color="#3b8ed0"
            )

    def _on_dnd_leave(self, event):
        """Restore normal frame styling on drag leave."""
        if hasattr(self, "drop_frame") and self.drop_frame.winfo_exists():
            self.drop_frame.configure(
                border_color=("#c0c0c0", "#3a3a3a"),
                border_width=2,
                fg_color=("#f5f5f5", "#1c1c1c")
            )
        elif hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text="", text_color="gray")

    def _on_dnd_drop(self, event):
        self._on_dnd_leave(event)
        raw_data = event.data
        if not raw_data:
            return

        try:
            paths = list(self.tk.splitlist(raw_data))
        except Exception:
            paths = [raw_data]

        self._filter_and_add_files(paths)

        if self.files:
            if hasattr(self, "drop_frame") and self.drop_frame.winfo_exists():
                self.after(0, self._transition_to_main_ui)
            else:
                self.after(0, self._update_file_count_display)
        else:
            if hasattr(self, "drop_subtext") and self.drop_subtext.winfo_exists():
                self.drop_subtext.configure(
                    text="Unsupported format! Drop JPG, PNG, WEBP, or AVIF",
                    text_color="#e74c3c"
                )

    def bring_to_front(self):
        """Brings the application window to the foreground."""
        def _focus():
            try:
                self.deiconify()
                self.lift()
                self.focus_force()
                self.attributes("-topmost", True)
                self.after(100, lambda: self.attributes("-topmost", False))
            except Exception:
                pass
        self.after(0, _focus)

    def add_files_from_external(self, new_paths: List[str]):
        """Callback for IPC socket when Windows Explorer forwards files."""
        self._filter_and_add_files(new_paths)
        if self.files:
            if hasattr(self, "drop_frame") and self.drop_frame.winfo_exists():
                self.after(0, self._transition_to_main_ui)
            else:
                self.after(0, self._update_file_count_display)
        self.bring_to_front()

    def _build_drop_ui(self):
        # Header
        self.title_label = ctk.CTkLabel(
            self.container,
            text="SizeWiz",
            font=ctk.CTkFont(family="Segoe UI Variable Display", size=21, weight="bold")
        )
        self.title_label.pack(pady=(0, 6))

        # Drop Zone Frame (clickable)
        self.drop_frame = ctk.CTkFrame(
            self.container,
            corner_radius=12,
            border_width=2,
            border_color=("#c0c0c0", "#3a3a3a"),
            fg_color=("#f5f5f5", "#1c1c1c"),
            cursor="hand2"
        )
        self.drop_frame.pack(fill="both", expand=True, pady=(0, 4))
        self.drop_frame.bind("<Button-1>", lambda e: self._on_browse_click())

        # Drop Zone Content
        self.drop_icon = ctk.CTkLabel(
            self.drop_frame,
            text="📁",
            font=ctk.CTkFont(size=36)
        )
        self.drop_icon.pack(pady=(24, 4))
        self.drop_icon.bind("<Button-1>", lambda e: self._on_browse_click())

        self.drop_text = ctk.CTkLabel(
            self.drop_frame,
            text="Drag & drop image(s) here",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.drop_text.pack(pady=(0, 2))
        self.drop_text.bind("<Button-1>", lambda e: self._on_browse_click())

        self.drop_subtext = ctk.CTkLabel(
            self.drop_frame,
            text="or click to browse",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray"
        )
        self.drop_subtext.pack(pady=(0, 6))
        self.drop_subtext.bind("<Button-1>", lambda e: self._on_browse_click())

        self.formats_label = ctk.CTkLabel(
            self.drop_frame,
            text="JPG · PNG · WEBP · AVIF",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#888888"
        )
        self.formats_label.pack(pady=(0, 12))
        self.formats_label.bind("<Button-1>", lambda e: self._on_browse_click())

    def _on_browse_click(self):
        selected = filedialog.askopenfilenames(
            title="Select image(s) to resize",
            filetypes=[
                ("Supported Images", "*.jpg;*.jpeg;*.png;*.webp;*.avif"),
                ("All files", "*.*")
            ]
        )
        if selected:
            self._filter_and_add_files(list(selected))
            if self.files:
                self._transition_to_main_ui()

    def _transition_to_main_ui(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        # Geometry stays identical (340x320)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._build_main_ui()

    def _build_main_ui(self):
        # 1. BOTTOM-DOCKING: Pack bottom elements first to guarantee visibility
        self.status_label = ctk.CTkLabel(
            self.container,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray",
            height=14
        )
        self.status_label.pack(side="bottom", fill="x", pady=(1, 0))

        self.resize_button = ctk.CTkButton(
            self.container,
            text=self._get_button_text(),
            command=self._on_resize_click,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.resize_button.pack(side="bottom", fill="x", pady=(6, 0))

        # Bundle in folder Checkbox (visible when >= 2 files)
        self.bundle_var = ctk.BooleanVar(value=self.config.get("bundle_in_folder", False))
        self.bundle_checkbox = ctk.CTkCheckBox(
            self.container,
            text="Bundle in folder",
            variable=self.bundle_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=5
        )
        self._update_bundle_visibility()

        # 2. TOP-DOCKING: Header, switch, and dimension entries (snug, no blank gaps)
        self.title_label = ctk.CTkLabel(
            self.container,
            text="SizeWiz",
            font=ctk.CTkFont(family="Segoe UI Variable Display", size=21, weight="bold")
        )
        self.title_label.pack(side="top", pady=(0, 6))

        saved_mode = self.config.get("mode", "downscale").capitalize()
        self.mode_switch = ctk.CTkSegmentedButton(
            self.container,
            values=["Downscale", "Upscale"],
            command=self._on_mode_change,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="normal"),
            height=30,
            corner_radius=8
        )
        self.mode_switch.set(saved_mode)
        self.mode_switch.pack(side="top", fill="x", pady=(0, 8))

        # Input Dimension Boxes Grid
        inputs_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        inputs_frame.pack(side="top", fill="x", pady=(0, 6))

        # Width
        self.width_col = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        self.width_col.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.width_label = ctk.CTkLabel(
            self.width_col,
            text="Max Width (px)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w"
        )
        self.width_label.pack(fill="x", pady=(0, 1))

        self.width_entry = ctk.CTkEntry(
            self.width_col,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            placeholder_text="Width (optional)"
        )
        self.width_entry.pack(fill="x")
        self.width_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())

        # Height
        self.height_col = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        self.height_col.pack(side="right", fill="both", expand=True, padx=(4, 0))

        self.height_label = ctk.CTkLabel(
            self.height_col,
            text="Max Height (px)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            anchor="w"
        )
        self.height_label.pack(fill="x", pady=(0, 1))

        self.height_entry = ctk.CTkEntry(
            self.height_col,
            height=32,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            placeholder_text="Height (optional)"
        )
        self.height_entry.pack(fill="x")
        self.height_entry.bind("<KeyRelease>", lambda e: self._validate_inputs())

        self._apply_mode(self.config.get("mode", "downscale"))
        self._validate_inputs()

    def _get_button_text(self) -> str:
        count = len(self.files)
        if count == 0:
            return "Resize (Select images)"
        elif count == 1:
            return "Resize (1 image)"
        else:
            return f"Resize ({count} images)"

    def _update_bundle_visibility(self):
        if len(self.files) >= 2:
            if not self.bundle_checkbox.winfo_ismapped():
                self.bundle_checkbox.pack(side="bottom", anchor="w", pady=(4, 4))
        else:
            if self.bundle_checkbox.winfo_ismapped():
                self.bundle_checkbox.pack_forget()

    def _update_file_count_display(self):
        self._update_bundle_visibility()
        self.resize_button.configure(text=self._get_button_text())
        self._validate_inputs()

    def _on_mode_change(self, value: str):
        mode = value.lower()
        self._save_current_dimensions()
        self._apply_mode(mode)
        self._validate_inputs()

    def _apply_mode(self, mode: str):
        self.config["mode"] = mode
        if mode == "downscale":
            self.width_label.configure(text="Max Width (px)")
            self.height_label.configure(text="Max Height (px)")
            self._set_entry(self.width_entry, self.config.get("downscale_max_w", "1920"))
            self._set_entry(self.height_entry, self.config.get("downscale_max_h", "1080"))
        else:
            self.width_label.configure(text="Min Width (px)")
            self.height_label.configure(text="Min Height (px)")
            self._set_entry(self.width_entry, self.config.get("upscale_min_w", "800"))
            self._set_entry(self.height_entry, self.config.get("upscale_min_h", "800"))

    def _set_entry(self, entry: ctk.CTkEntry, value: str):
        entry.delete(0, "end")
        if value:
            entry.insert(0, str(value))

    def _validate_inputs(self):
        """
        Ensures at least one of the 2 fields has a valid positive integer value.
        If both are blank/invalid, the resize button is grayed out.
        """
        w_val = None
        h_val = None

        w_str = self.width_entry.get().strip()
        if w_str:
            try:
                val = int(w_str)
                if val > 0:
                    w_val = val
            except ValueError:
                pass

        h_str = self.height_entry.get().strip()
        if h_str:
            try:
                val = int(h_str)
                if val > 0:
                    h_val = val
            except ValueError:
                pass

        has_valid_dimension = (w_val is not None) or (h_val is not None)
        has_files = len(self.files) > 0

        if has_valid_dimension and has_files:
            self.resize_button.configure(state="normal")
            if self.status_label.cget("text") == "Enter at least one dimension":
                self.status_label.configure(text="")
        else:
            self.resize_button.configure(state="disabled")
            if not has_valid_dimension and has_files:
                self.status_label.configure(
                    text="Enter at least one dimension",
                    text_color="gray"
                )

    def _save_current_dimensions(self):
        if not hasattr(self, "mode_switch"):
            return
        mode = self.mode_switch.get().lower()
        w_text = self.width_entry.get().strip()
        h_text = self.height_entry.get().strip()

        if mode == "downscale":
            self.config["downscale_max_w"] = w_text
            self.config["downscale_max_h"] = h_text
        else:
            self.config["upscale_min_w"] = w_text
            self.config["upscale_min_h"] = h_text

        self.config["bundle_in_folder"] = self.bundle_var.get()
        save_config(self.config)

    def _on_resize_click(self):
        if not self.files:
            self._on_browse_click()
            return

        self._save_current_dimensions()

        mode = self.mode_switch.get().lower()
        w_val = None
        h_val = None
        try:
            w_str = self.width_entry.get().strip()
            if w_str:
                w_val = int(w_str)
        except ValueError:
            pass

        try:
            h_str = self.height_entry.get().strip()
            if h_str:
                h_val = int(h_str)
        except ValueError:
            pass

        if not w_val and not h_val:
            self._validate_inputs()
            return

        bundle = self.bundle_var.get() if len(self.files) >= 2 else False

        self.resize_button.configure(state="disabled", text="Resizing...")
        self.status_label.configure(text="Processing images...", text_color="gray")

        thread = threading.Thread(
            target=self._process_batch_thread,
            args=(self.files, mode, w_val, h_val, bundle),
            daemon=True
        )
        thread.start()

    def _process_batch_thread(self, files: List[Path], mode: str, w: Optional[int], h: Optional[int], bundle: bool):
        resized_count = 0
        skipped_count = 0

        for f in files:
            res = process_image(f, mode, w, h, bundle_in_folder=bundle)
            if res.status == "resized":
                resized_count += 1
            elif res.status == "skipped":
                skipped_count += 1

        self.after(0, lambda: self._on_batch_complete(resized_count, skipped_count, len(files)))

    def _on_batch_complete(self, resized: int, skipped: int, total: int):
        self.status_label.configure(
            text=f"Done! ({resized} resized, {skipped} skipped)",
            text_color="#2ecc71"
        )
        self.resize_button.configure(text="Complete!")

        # Smooth auto-close after 0.7 seconds
        self.after(700, self.destroy)
