import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple, NamedTuple, Any

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

class ResizeResult(NamedTuple):
    source_path: Path
    output_path: Optional[Path]
    status: str  # "resized", "skipped", "error"
    orig_size: Tuple[int, int]
    new_size: Optional[Tuple[int, int]]
    error_message: Optional[str] = None


class BaseResizerEngine(ABC):
    @abstractmethod
    def resize(self, image: Any, target_size: Tuple[int, int]) -> Any:
        """Resize the given PIL Image to the target size."""
        pass


class LanczosResizerEngine(BaseResizerEngine):
    """High-precision sinc-windowed Lanczos resampling engine."""
    def resize(self, image: Any, target_size: Tuple[int, int]) -> Any:
        from PIL import Image
        return image.resize(target_size, Image.Resampling.LANCZOS)


class AIResizerEngine(BaseResizerEngine):
    """Placeholder slot for future ONNX/Real-ESRGAN super-resolution upscaler."""
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def resize(self, image: Any, target_size: Tuple[int, int]) -> Any:
        from PIL import Image
        return image.resize(target_size, Image.Resampling.LANCZOS)


def calculate_target_dimensions(
    orig_w: int,
    orig_h: int,
    mode: str,
    target_w: Optional[int],
    target_h: Optional[int]
) -> Optional[Tuple[int, int]]:
    """
    Calculates the new dimensions while strictly preserving aspect ratio.
    Returns None if the image already satisfies the constraints (skip conversion).
    """
    if orig_w <= 0 or orig_h <= 0:
        return None

    # Filter out empty or non-positive targets
    req_w = target_w if (target_w is not None and target_w > 0) else None
    req_h = target_h if (target_h is not None and target_h > 0) else None

    if req_w is None and req_h is None:
        return None

    if mode == "downscale":
        # Check if already within limits
        w_ok = (req_w is None) or (orig_w <= req_w)
        h_ok = (req_h is None) or (orig_h <= req_h)
        if w_ok and h_ok:
            return None  # Already obeys max dimensions!

        # Scale down to fit within bounding box
        scales = []
        if req_w is not None:
            scales.append(req_w / orig_w)
        if req_h is not None:
            scales.append(req_h / orig_h)
        
        s = min(scales)
        new_w = max(1, round(orig_w * s))
        new_h = max(1, round(orig_h * s))

        # Precision guard to ensure neither dimension exceeds limit due to rounding
        if req_w is not None and new_w > req_w:
            new_w = req_w
            new_h = max(1, round(orig_h * (req_w / orig_w)))
        if req_h is not None and new_h > req_h:
            new_h = req_h
            new_w = max(1, round(orig_w * (req_h / orig_h)))

        return new_w, new_h

    elif mode == "upscale":
        # Check if already meets or exceeds minimums
        w_ok = (req_w is None) or (orig_w >= req_w)
        h_ok = (req_h is None) or (orig_h >= req_h)
        if w_ok and h_ok:
            return None  # Already obeys min dimensions!

        # Scale up to satisfy both minimums
        scales = []
        if req_w is not None:
            scales.append(req_w / orig_w)
        if req_h is not None:
            scales.append(req_h / orig_h)

        s = max(scales)
        new_w = max(1, round(orig_w * s))
        new_h = max(1, round(orig_h * s))

        # Guard to ensure both minimums are satisfied
        if req_w is not None and new_w < req_w:
            new_w = req_w
        if req_h is not None and new_h < req_h:
            new_h = req_h

        return new_w, new_h

    return None


def get_available_output_path(
    source_path: Path,
    mode: str,
    bundle_in_folder: bool
) -> Path:
    """
    Generates a unique destination path adhering to naming rules and collision counters.
    Example:
      photo.png -> photo_down.png
      If photo_down.png exists -> photo_down_1.png -> photo_down_2.png
    """
    suffix_tag = "down" if mode == "downscale" else "upsc"
    parent_dir = source_path.parent / "SizeWiz" if bundle_in_folder else source_path.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    stem = source_path.stem
    ext = source_path.suffix

    candidate = parent_dir / f"{stem}_{suffix_tag}{ext}"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = parent_dir / f"{stem}_{suffix_tag}_{counter}{ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def process_image(
    source_path: Path,
    mode: str,
    target_w: Optional[int],
    target_h: Optional[int],
    bundle_in_folder: bool = False,
    engine: Optional[BaseResizerEngine] = None
) -> ResizeResult:
    """Processes a single image file."""
    if engine is None:
        engine = LanczosResizerEngine()

    source_path = Path(source_path)
    if not source_path.is_file():
        return ResizeResult(source_path, None, "error", (0, 0), None, "File does not exist")

    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return ResizeResult(
            source_path, None, "error", (0, 0), None,
            f"Unsupported format {source_path.suffix}"
        )

    try:
        from PIL import Image, ImageOps
        with Image.open(source_path) as img:
            # Handle orientation from EXIF metadata (e.g. phone camera photos)
            img = ImageOps.exif_transpose(img)
            orig_size = img.size

            target_size = calculate_target_dimensions(
                orig_size[0], orig_size[1], mode, target_w, target_h
            )

            # If image already obeys dimensions, skip without saving
            if target_size is None:
                return ResizeResult(source_path, None, "skipped", orig_size, None)

            # Perform the resize
            resized_img = engine.resize(img, target_size)

            output_path = get_available_output_path(source_path, mode, bundle_in_folder)

            # Preserve format and metadata
            ext = source_path.suffix.lower()
            save_kwargs = {}
            exif = img.info.get("exif")
            if exif:
                save_kwargs["exif"] = exif

            if ext in {".jpg", ".jpeg"}:
                save_kwargs.update({"quality": 95, "optimize": True})
                if resized_img.mode in ("RGBA", "LA", "P"):
                    # Flatten alpha onto pure white background for JPEG
                    bg = Image.new("RGB", resized_img.size, (255, 255, 255))
                    alpha = resized_img.convert("RGBA").split()[-1]
                    bg.paste(resized_img, mask=alpha)
                    resized_img = bg
                elif resized_img.mode != "RGB":
                    resized_img = resized_img.convert("RGB")
            elif ext == ".png":
                save_kwargs.update({"optimize": True})
            elif ext == ".webp":
                save_kwargs.update({"quality": 95, "method": 6})
            elif ext == ".avif":
                save_kwargs.update({"quality": 95})

            resized_img.save(output_path, **save_kwargs)
            return ResizeResult(source_path, output_path, "resized", orig_size, target_size)

    except Exception as e:
        return ResizeResult(source_path, None, "error", (0, 0), None, str(e))
