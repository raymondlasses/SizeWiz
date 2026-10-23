import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from core.resizer import (
    calculate_target_dimensions,
    get_available_output_path,
    process_image,
    SUPPORTED_EXTENSIONS
)

class TestResizer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_downscale_dimensions_landscape(self):
        # 4000 x 2000 -> max 1920 x 1080
        # Scale is min(1920/4000 = 0.48, 1080/2000 = 0.54) = 0.48
        # Target: 4000 * 0.48 = 1920, 2000 * 0.48 = 960
        res = calculate_target_dimensions(4000, 2000, "downscale", 1920, 1080)
        self.assertEqual(res, (1920, 960))

    def test_downscale_dimensions_portrait(self):
        # 2000 x 4000 -> max 1920 x 1080
        # Scale is min(1920/2000 = 0.96, 1080/4000 = 0.27) = 0.27
        # Target: 2000 * 0.27 = 540, 4000 * 0.27 = 1080
        res = calculate_target_dimensions(2000, 4000, "downscale", 1920, 1080)
        self.assertEqual(res, (540, 1080))

    def test_downscale_skip_when_already_compliant(self):
        # 800 x 600 is within 1920 x 1080 -> should return None
        res = calculate_target_dimensions(800, 600, "downscale", 1920, 1080)
        self.assertIsNone(res)

    def test_downscale_single_dimension(self):
        # Only max width specified
        res = calculate_target_dimensions(4000, 2000, "downscale", 1000, None)
        self.assertEqual(res, (1000, 500))

        # Only max height specified
        res = calculate_target_dimensions(4000, 2000, "downscale", None, 500)
        self.assertEqual(res, (1000, 500))

    def test_upscale_dimensions_both_minimums(self):
        # 400 x 200 -> min 800 x 800
        # Scale is max(800/400 = 2.0, 800/200 = 4.0) = 4.0
        # Target: 400 * 4.0 = 1600, 200 * 4.0 = 800
        # Satisfies min width >= 800 and min height >= 800 while keeping 2:1 aspect ratio!
        res = calculate_target_dimensions(400, 200, "upscale", 800, 800)
        self.assertEqual(res, (1600, 800))

    def test_upscale_skip_when_already_compliant(self):
        # 1200 x 900 already satisfies min 800 x 800 -> should return None
        res = calculate_target_dimensions(1200, 900, "upscale", 800, 800)
        self.assertIsNone(res)

    def test_upscale_single_dimension(self):
        res = calculate_target_dimensions(400, 200, "upscale", 800, None)
        self.assertEqual(res, (800, 400))

    def test_output_naming_collision_and_bundling(self):
        test_file = self.test_dir / "sample.png"
        test_file.touch()

        # Regular output without bundle
        out1 = get_available_output_path(test_file, "downscale", bundle_in_folder=False)
        self.assertEqual(out1.name, "sample_down.png")
        self.assertEqual(out1.parent, self.test_dir)
        out1.touch()  # Create it

        # Next output should have collision counter _1
        out2 = get_available_output_path(test_file, "downscale", bundle_in_folder=False)
        self.assertEqual(out2.name, "sample_down_1.png")
        out2.touch()

        # Next should be _2
        out3 = get_available_output_path(test_file, "downscale", bundle_in_folder=False)
        self.assertEqual(out3.name, "sample_down_2.png")

        # Bundled output
        bundle_out = get_available_output_path(test_file, "downscale", bundle_in_folder=True)
        self.assertEqual(bundle_out.name, "sample_down.png")
        self.assertEqual(bundle_out.parent.name, "SizeWiz")
        self.assertEqual(bundle_out.parent.parent, self.test_dir)

    def test_process_image_formats(self):
        for ext in [".jpg", ".png", ".webp", ".avif"]:
            img_path = self.test_dir / f"test{ext}"
            img = Image.new("RGB", (2000, 1000), color=(100, 150, 200))
            if ext == ".avif":
                img.save(img_path, "AVIF")
            else:
                img.save(img_path)

            result = process_image(img_path, "downscale", 1000, 500)
            self.assertEqual(result.status, "resized", f"Failed on {ext}: {result.error_message}")
            self.assertTrue(result.output_path.exists())
            self.assertEqual(result.new_size, (1000, 500))

            # Verify the output image dimensions
            with Image.open(result.output_path) as out_img:
                self.assertEqual(out_img.size, (1000, 500))

if __name__ == "__main__":
    unittest.main()
