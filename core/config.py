import os
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "mode": "downscale",  # "downscale" or "upscale"
    "downscale_max_w": "1920",
    "downscale_max_h": "1080",
    "upscale_min_w": "800",
    "upscale_min_h": "800",
    "bundle_in_folder": False
}

def get_config_path() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        base_dir = Path(app_data) / "SizeWiz"
    else:
        base_dir = Path.home() / ".sizewiz"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "config.json"

def load_config() -> dict:
    config_file = get_config_path()
    config = dict(DEFAULT_CONFIG)
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    config.update(saved)
        except Exception:
            pass
    return config

def save_config(config: dict) -> None:
    config_file = get_config_path()
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass
