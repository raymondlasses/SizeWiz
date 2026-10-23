import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

VERSION = "v1"

def run_cmd(cmd, description):
    print(f"\n==========================================")
    print(f"[*] {description}...")
    print(f"==========================================")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"[!] ERROR: {description} failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def zip_directory(folder_path: Path, output_zip: Path):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(folder_path)
                zf.write(abs_path, rel_path)

def main():
    root_dir = Path(__file__).resolve().parent
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    # Step 1: Clean previous build artifacts
    print("[*] Cleaning build/dist directories...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir, ignore_errors=True)
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    # Step 2: Build SizeWiz native fast directory (for instant ~200ms launch)
    cmd_onedir = (
        'pyinstaller --noconfirm --onedir --windowed '
        '--name "SizeWiz" '
        '--collect-all customtkinter '
        '--collect-all tkinterdnd2 '
        '--collect-all PIL '
        'main.py'
    )
    run_cmd(cmd_onedir, "Compiling SizeWiz Native Fast Directory")

    sizewiz_dir = dist_dir / "SizeWiz"
    if not sizewiz_dir.exists():
        print(f"[!] SizeWiz directory not found at {sizewiz_dir}")
        sys.exit(1)

    # Zip the fast application directory into payload for installer
    print("[*] Packaging fast payload zip for setup wizard...")
    payload_zip = dist_dir / "sizewiz_payload.zip"
    zip_directory(sizewiz_dir, payload_zip)

    # Step 3: Also build standalone portable single-file SizeWiz.exe
    cmd_onefile = (
        'pyinstaller --noconfirm --onefile --windowed '
        '--name "SizeWiz_Portable" '
        '--collect-all customtkinter '
        '--collect-all tkinterdnd2 '
        '--collect-all PIL '
        'main.py'
    )
    run_cmd(cmd_onefile, "Compiling SizeWiz Portable Single-File")

    # Step 4: Build SizeWiz_v1_Setup.exe bundling the fast payload zip
    setup_name = f"SizeWiz_{VERSION}_Setup"
    cmd_setup = (
        f'pyinstaller --noconfirm --onefile --windowed '
        f'--name "{setup_name}" '
        f'--paths . '
        f'--collect-all customtkinter '
        f'--add-data "{str(payload_zip)};." '
        f'installer/setup_wizard.py'
    )
    run_cmd(cmd_setup, f"Compiling {setup_name}.exe")

    release_setup = dist_dir / f"{setup_name}.exe"
    portable_exe = dist_dir / "SizeWiz_Portable.exe"

    # Step 5: Create Portable Zip
    print("[*] Creating portable zip distribution...")
    portable_zip = root_dir / f"SizeWiz_{VERSION}_Portable.zip"
    shutil.make_archive(root_dir / f"SizeWiz_{VERSION}_Portable", "zip", sizewiz_dir)

    # Step 6: Copy executables to root directory for easy access
    print("[*] Copying release files to root directory...")
    shutil.copy2(portable_exe, root_dir / "SizeWiz.exe")
    shutil.copy2(release_setup, root_dir / f"{setup_name}.exe")

    # Clean up any old unversioned setup exe if it exists
    old_setup = root_dir / "SizeWiz_Setup.exe"
    if old_setup.exists():
        try:
            old_setup.unlink()
        except Exception:
            pass

    # Clean up .spec files
    for spec_file in root_dir.glob("*.spec"):
        try:
            spec_file.unlink()
        except Exception:
            pass

    print(f"\n==========================================")
    print(f"[+] BUILD SUCCESSFUL!")
    print(f"[+] Installer Wizard:   {root_dir / f'{setup_name}.exe'}")
    print(f"[+] Portable Zip:       {portable_zip}")
    print(f"[+] Standalone Exe:     {root_dir / 'SizeWiz.exe'}")
    print(f"==========================================")

if __name__ == "__main__":
    main()
