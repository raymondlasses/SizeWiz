import os
import sys
import winreg
from pathlib import Path
import ctypes

def notify_shell_associations_changed():
    """Notifies Windows Explorer that file associations have been updated."""
    try:
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass

def create_shortcut(target_exe: Path, shortcut_path: Path, description: str = "SizeWiz Image Resizer"):
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = str(target_exe)
        shortcut.WorkingDirectory = str(target_exe.parent)
        shortcut.Description = description
        shortcut.IconLocation = str(target_exe)
        shortcut.Save()
    except Exception:
        import subprocess
        ps_cmd = (
            f"$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{str(shortcut_path)}'); "
            f"$s.TargetPath = '{str(target_exe)}'; "
            f"$s.WorkingDirectory = '{str(target_exe.parent)}'; "
            f"$s.Save()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)

def register_open_with(target_exe: Path):
    """
    Registers SizeWiz in Windows HKCU registry for Open With and image file associations.
    """
    exe_str = f'"{str(target_exe)}" "%1"'
    formats = [".jpg", ".jpeg", ".png", ".webp", ".avif"]

    # 1. Applications key
    app_base = r"Software\Classes\Applications\SizeWiz.exe"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_base) as key:
        winreg.SetValueEx(key, "FriendlyAppName", 0, winreg.REG_SZ, "SizeWiz")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_base}\DefaultIcon") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, f'"{str(target_exe)}",0')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_base}\shell\open\command") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, exe_str)

    # Supported Types
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_base}\SupportedTypes") as key:
        for ext in formats:
            winreg.SetValueEx(key, ext, 0, winreg.REG_SZ, "")

    # 2. SystemFileAssociations for all images
    sfa_key_path = r"Software\Classes\SystemFileAssociations\image\OpenWithList\SizeWiz.exe"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sfa_key_path) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, "")

    # 3. SizeWiz.Image ProgID
    progid_path = r"Software\Classes\SizeWiz.Image"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, progid_path) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, "SizeWiz Image File")
        winreg.SetValueEx(key, "FriendlyTypeName", 0, winreg.REG_SZ, "SizeWiz Image File")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{progid_path}\DefaultIcon") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, f'"{str(target_exe)}",0')

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{progid_path}\shell\open\command") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, exe_str)

    # 4. Bind ProgID & OpenWithList to extensions
    for ext in formats:
        # OpenWithProgids
        ext_progid_path = rf"Software\Classes\{ext}\OpenWithProgids"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ext_progid_path) as key:
            winreg.SetValueEx(key, "SizeWiz.Image", 0, winreg.REG_SZ, "")

        # OpenWithList
        ext_owl_path = rf"Software\Classes\{ext}\OpenWithList\SizeWiz.exe"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ext_owl_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "")

    # Notify Windows Explorer
    notify_shell_associations_changed()

def register_uninstall_entry(target_dir: Path, target_exe: Path):
    """
    Adds SizeWiz to Windows 'Installed Apps' / 'Add or Remove Programs' in Control Panel / Settings.
    """
    uninstall_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SizeWiz"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_key_path) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "SizeWiz")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "SizeWiz")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{str(target_exe)}" --uninstall')
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{str(target_exe)}",0')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

def unregister_all():
    """Removes all SizeWiz registry entries cleanly."""
    formats = [".jpg", ".jpeg", ".png", ".webp", ".avif"]

    def delete_key_tree(root, subkey):
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        child = winreg.EnumKey(k, 0)
                        delete_key_tree(k, child)
                    except OSError:
                        break
            winreg.DeleteKey(root, subkey)
        except OSError:
            pass

    for ext in formats:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, "SizeWiz.Image")
                except OSError:
                    pass
        except OSError:
            pass

        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\OpenWithList\SizeWiz.exe")

    delete_key_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\Applications\SizeWiz.exe")
    delete_key_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\SystemFileAssociations\image\OpenWithList\SizeWiz.exe")
    delete_key_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\SizeWiz.Image")
    delete_key_tree(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SizeWiz")

    notify_shell_associations_changed()
