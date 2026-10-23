import unittest
from pathlib import Path
from PIL import Image
from core.resizer import process_image, calculate_target_dimensions, LanczosResizerEngine


class TestPerformanceAndEngines(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/test_output_perf")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.img_path = self.test_dir / "perf_test.png"
        img = Image.new("RGB", (200, 150), (100, 150, 200))
        img.save(self.img_path)

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_smart_resizer_modes(self):
        engine = LanczosResizerEngine()
        img = Image.new("RGB", (100, 100), (255, 0, 0))

        # Downscale mode
        down = engine.resize(img, (50, 50), mode="downscale")
        self.assertEqual(down.size, (50, 50))

        # Upscale mode
        up = engine.resize(img, (200, 200), mode="upscale")
        self.assertEqual(up.size, (200, 200))

    def test_parallel_batch_execution(self):
        from concurrent.futures import ThreadPoolExecutor

        files = []
        for i in range(4):
            p = self.test_dir / f"batch_{i}.png"
            img = Image.new("RGB", (300, 200), (i * 40, 100, 100))
            img.save(p)
            files.append(p)

        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(lambda f: process_image(f, "upscale", 378, None), files))

        self.assertEqual(len(results), 4)
        for r in results:
            self.assertEqual(r.status, "resized")
            self.assertEqual(r.new_size, (378, 252))
            self.assertTrue(r.output_path.exists())


if __name__ == "__main__":
    unittest.main()
