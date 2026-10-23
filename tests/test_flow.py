import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from core.resizer import process_image

class TestFullFlow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.img1 = self.temp_dir / "large.jpg"
        self.img2 = self.temp_dir / "small.png"
        self.img3 = self.temp_dir / "square.webp"

        Image.new("RGB", (3000, 1500), color="blue").save(self.img1)
        Image.new("RGBA", (500, 250), color="red").save(self.img2)
        Image.new("RGB", (400, 400), color="green").save(self.img3)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_downscale_bundle_flow(self):
        # Downscale with max 1920x1080 and bundle=True
        res1 = process_image(self.img1, "downscale", 1920, 1080, bundle_in_folder=True)
        res2 = process_image(self.img2, "downscale", 1920, 1080, bundle_in_folder=True)
        res3 = process_image(self.img3, "downscale", 1920, 1080, bundle_in_folder=True)

        self.assertEqual(res1.status, "resized")
        self.assertEqual(res1.new_size, (1920, 960))
        self.assertTrue(res1.output_path.exists())
        self.assertEqual(res1.output_path.parent.name, "SizeWiz")

        # img2 is 500x250, within 1920x1080, should be skipped
        self.assertEqual(res2.status, "skipped")
        self.assertIsNone(res2.output_path)

        # img3 is 400x400, within 1920x1080, should be skipped
        self.assertEqual(res3.status, "skipped")
        self.assertIsNone(res3.output_path)

    def test_upscale_flow(self):
        # Upscale with min 1000x1000
        # img1 (3000x1500) already >= 1000 in both dimensions -> skipped!
        res1 = process_image(self.img1, "upscale", 1000, 1000, bundle_in_folder=False)
        self.assertEqual(res1.status, "skipped")

        # img2 (500x250) -> min 1000x1000
        # scale = max(1000/500 = 2, 1000/250 = 4) = 4
        # target = 2000 x 1000
        res2 = process_image(self.img2, "upscale", 1000, 1000, bundle_in_folder=False)
        self.assertEqual(res2.status, "resized")
        self.assertEqual(res2.new_size, (2000, 1000))
        self.assertEqual(res2.output_path.name, "small_upsc.png")
        self.assertTrue(res2.output_path.exists())

if __name__ == "__main__":
    unittest.main()
