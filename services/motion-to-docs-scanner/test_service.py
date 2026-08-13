import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MOTION_SCANNER_BUCKET", "test-bucket")

from PIL import Image, ImageDraw
from service import choose_unique_frames, make_contact_sheets


class ScannerTests(unittest.TestCase):
    def test_exact_duplicate_collapses_and_distinct_frame_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = []
            for index, x in enumerate((8, 8, 42)):
                image = Image.new("RGB", (96, 64), "black")
                ImageDraw.Draw(image).rectangle((x, 12, x + 24, 48), fill="white")
                path = root / f"frame_{index:09d}.png"
                image.save(path)
                paths.append(path)
            kept, manifest, duplicate_counts = choose_unique_frames(paths, threshold=0, fps=30.0)
            self.assertEqual(2, len(kept))
            self.assertEqual(0, manifest[0]["keptIndex"])
            self.assertEqual(0, manifest[1]["duplicateOf"])
            self.assertEqual(1, manifest[2]["keptIndex"])
            self.assertEqual(1, duplicate_counts[0])
            self.assertAlmostEqual(2 / 30.0, manifest[2]["timestampSeconds"], places=6)

    def test_contact_sheet_is_created(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frame = root / "frame.png"
            Image.new("RGB", (64, 64), "white").save(frame)
            rows = [{"sourceFrame": 12, "timestampSeconds": 0.4, "keptIndex": 0}]
            sheets = make_contact_sheets([frame], rows, [3], root)
            self.assertEqual(1, len(sheets))
            self.assertTrue(sheets[0].exists())
            self.assertGreater(sheets[0].stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
