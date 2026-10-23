# SizeWiz

<p align="center">
  <b>Smart, lightweight, and snappy image downscaler/upscaler for Windows.</b><br>
  Built for quick resizing via Windows Explorer's <i>"Open with"</i> menu or drag-and-drop.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue?logo=windows" alt="Platform Windows" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License MIT" />
  <img src="https://img.shields.io/badge/Formats-JPG%20%7C%20PNG%20%7C%20WEBP%20%7C%20AVIF-orange" alt="Supported Formats" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python" alt="Python 3.10+" />
</p>

---

## ✨ Why SizeWiz?

Satisfying website upload constraints (e.g. *"Max dimensions: 1920x1080"* or *"Must be at least 800x800"*) is usually frustrating. People either open heavy editors like Photoshop, fiddle with command line tools, or upload private photos to ad-ridden online converters.

**SizeWiz** solves this with a lightweight utility:
1. Select one or more images anywhere on your desktop or file explorer.
2. Right-click $\rightarrow$ **Open with $\rightarrow$ SizeWiz** (or drag & drop onto the standalone app).
3. Choose your bounding dimensions and click **Resize**.
4. The resized images appear in the same folder (or grouped in a `SizeWiz/` subfolder), and the window automatically closes!

---

## 🚀 Key Features

* **Windows Explorer Context Menu & Multi-Select**:
  * **Single Image**: Right-click $\rightarrow$ **Open with $\rightarrow$ SizeWiz** or **Resize with SizeWiz**.
  * **Multiple Images**: Select 2 or more images $\rightarrow$ hold **`Shift + Right-Click`** $\rightarrow$ **Resize with SizeWiz** (or **Send to $\rightarrow$ SizeWiz**).
  * **Single-Instance Mutex & Bundling**: Even when Windows launches multiple processes in parallel, SizeWiz atomically groups all selected files into **a single window**!
* **Blazing Fast Multi-Core Engine**:
  * **Parallel Batch Processing**: Concurrently processes multiple images across all available CPU cores using a multi-threaded worker pool (~7x speedup on batch resizing).
  * **Smart Adaptive Resampling**:
    * **Downscale**: High-precision sinc-windowed **Lanczos** interpolation for crisp, sharp edge preservation.
    * **Upscale**: Smooth **Bicubic** interpolation (industry-standard for enlargement) eliminating ringing artifacts while running 2x faster.
  * **Optimized Compression**: Lossless PNG, high-fidelity WebP (method 4), and JPEG (Q=95) without redundant CPU-draining filter sweeps.
* **Zero-Distortion Aspect Ratio**:
  * **Downscale Mode**: Proportionally fits the image inside `Max Width × Max Height`. Never crops or stretches.
  * **Upscale Mode**: Scales the image up to satisfy **both** `Min Width` and `Min Height` requirements while strictly preserving aspect ratio.
  * **Single-Axis Mode**: Leave either width or height blank to scale based purely on a single dimension.
* **Smart Skip Logic**: If an image already obeys the requested bounds, SizeWiz skips it without creating redundant duplicates.
* **Collision Protection**: If `photo_down.png` already exists, SizeWiz appends incrementing counters (`photo_down_1.png`, `photo_down_2.png`).
* **Bundle in Folder**: When 2 or more images are selected, an optional `"Bundle in folder"` checkbox groups all outputs into a clean `./SizeWiz/` subfolder.
* **Format Support**: Native handling for **JPG, JPEG, PNG (with alpha), WEBP (with alpha), and AVIF** with automatic EXIF orientation preservation.
* **Modern Windows 11 UI**:
  * Automatically follows your Windows system theme (Dark / Light mode).
  * Blended caption title bar matching the window background via Windows DWM API.
  * Compact footprint (`340 × 320 px`) with no awkward blank gaps.
  * Blue glow visual feedback when dragging images over the window.
  * Dynamic action button: `Resize (N images)` with smooth auto-close on finish.
* **Snappy Performance**:
  * Native pre-extracted installation launches in **~0.25 seconds** (no `%TEMP%` extraction lag).
  * Native C/SIMD resampling via high-precision Lanczos sinc interpolation.

---

## 📥 Download & Installation

### Option 1: Installer (Recommended)
Download the latest **`SizeWiz_v1_Setup.exe`** from [GitHub Releases](https://github.com/raymondlasses/SizeWiz/releases):
1. Run `SizeWiz_v1_Setup.exe`.
2. Keep the integration options checked:
   - `[x] Register in Windows "Open with" menu`
   - `[x] Create Start Menu shortcut`
   - `[x] Create Desktop shortcut`
3. Click **Install SizeWiz**.
4. That's it! It installs cleanly to `%LOCALAPPDATA%\Programs\SizeWiz` (no Administrator UAC prompt required) and is fully integrated into Windows.

### Option 2: Portable (No Installation)
Download **`SizeWiz_v1_Portable.zip`**, extract it anywhere, and launch `SizeWiz.exe` directly.

---

## 💡 Windows 11 Multi-Image Resizing Tip

In Windows 11, Microsoft's File Explorer hides classic shell options and the *"Open with"* menu whenever more than one file is selected.

To quickly resize multiple images together in one click:
- Select 2 or more images in File Explorer.
- Hold **`Shift`** and **Right-Click** on any of the selected files.
- Select **Resize with SizeWiz** from the menu.

SizeWiz will immediately gather all selected files into a single window, process them in parallel across your CPU cores, and save the resized images directly.

---

## 🛠️ Building from Source

### Prerequisites
- Python 3.10+
- Windows 10 or 11

### Installation
```powershell
# Clone the repository
git clone https://github.com/raymondlasses/SizeWiz.git
cd SizeWiz

# Install dependencies
pip install customtkinter tkinterdnd2 pillow pyinstaller
```

### Run Locally
```powershell
# Run standalone
python main.py

# Run with test files
python main.py sample1.jpg sample2.png
```

### Run Tests
```powershell
python -m unittest discover tests
```

### Compile Standalone Executables
```powershell
python build.py
```
This builds:
* `SizeWiz_v1_Setup.exe`: Self-contained setup wizard ready for distribution.
* `SizeWiz.exe`: Standalone portable executable.
* `SizeWiz_v1_Portable.zip`: Pre-extracted portable archive.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
