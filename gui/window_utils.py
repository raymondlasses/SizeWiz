import ctypes
from ctypes import wintypes
import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

def apply_titlebar_styling(window, is_dark: bool = True):
    """
    Applies modern seamless titlebar blending via Windows DWM API.
    Matches the titlebar caption color to the window background.
    """
    if sys.platform != "win32":
        return

    try:
        window.update_idletasks()
        # In Tkinter, window.winfo_id() gives the window handle,
        # but for top-level windows on Windows, GetParent gives the top-level frame HWND
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()

        # Set dark/light mode for titlebar controls
        dark_flag = ctypes.c_int(1 if is_dark else 0)
        # Try Windows 11 / Windows 10 20H1+
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_flag),
            ctypes.sizeof(dark_flag)
        )
        if res != 0:
            # Fallback for earlier Windows 10 builds
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                ctypes.byref(dark_flag),
                ctypes.sizeof(dark_flag)
            )

        # Background color: #242424 for dark, #ebebeb for light
        # COLORREF format is 0x00BBGGRR
        if is_dark:
            color = ctypes.c_int(0x00242424)
        else:
            color = ctypes.c_int(0x00EBEBEB)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(color),
            ctypes.sizeof(color)
        )
    except Exception:
        # Graceful fallback if on unsupported Windows builds or wine
        pass
