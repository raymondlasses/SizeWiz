import unittest
from pathlib import Path
from PIL import Image
import winreg

from gui.app import get_icon_path
from installer.setup_wizard import get_installer_icon_path


class TestRegistryAndIcon(unittest.TestCase):
    def test_icon_assets_exist_and_valid(self):
        root = Path(__file__).resolve().parent.parent
        icon_ico = root / "assets" / "icon.ico"
        icon_png = root / "assets" / "icon.png"

        self.assertTrue(icon_ico.exists(), "assets/icon.ico must exist")
        self.assertTrue(icon_png.exists(), "assets/icon.png must exist")

        with Image.open(icon_png) as img:
            self.assertEqual(img.size, (256, 256))

        with Image.open(icon_ico) as img:
            self.assertGreater(img.size[0], 0)

    def test_get_icon_path_resolvers(self):
        app_icon = get_icon_path()
        self.assertIsNotNone(app_icon)
        self.assertTrue(app_icon.exists())

        installer_icon = get_installer_icon_path()
        self.assertIsNotNone(installer_icon)
        self.assertTrue(installer_icon.exists())


if __name__ == "__main__":
    unittest.main()
