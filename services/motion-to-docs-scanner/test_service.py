import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("MOTION_SCANNER_BUCKET", "test-bucket")

from PIL import Image, ImageDraw
from service import (
    choose_unique_frames,
    extract_frames,
    make_contact_sheets,
    make_unique_frame_archive,
    probe_video,
    validate_source_url,
)


class ScannerTests(unittest.TestCase):
    def make_frames(self, root):
        paths = []
        for index, x in enumerate((8, 8, 42)):
            image = Image.new("RGB", (96, 64), "black")
            ImageDraw.Draw(image).rectangle((x, 12, x + 24, 48), fill="white")
            path = root / f"frame_{index:09d}.png"
            image.save(path)
            paths.append(path)
        return paths

    def test_exact_duplicate_collapses_and_distinct_frame_survives(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.make_frames(Path(temp))
            kept, manifest, counts = choose_unique_frames(paths, mode="exact", threshold=0, fps=30.0)
            self.assertEqual(2, len(kept))
            self.assertEqual("sha256-rgb", manifest[0]["hashType"])
            self.assertEqual(0, manifest[1]["duplicateOf"])
            self.assertEqual(1, counts[0])
            self.assertAlmostEqual(2 / 30.0, manifest[2]["timestampSeconds"], places=6)

    def test_perceptual_mode_collapses_identical_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.make_frames(Path(temp))
            kept, manifest, _ = choose_unique_frames(paths, mode="perceptual", threshold=0, fps=24.0)
            self.assertEqual(2, len(kept))
            self.assertEqual("dhash-256", manifest[0]["hashType"])
            self.assertEqual(0, manifest[1]["duplicateOf"])

    def test_contact_sheet_and_unique_archive_are_created(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frame = root / "frame.png"
            Image.new("RGB", (64, 64), "white").save(frame)
            rows = [{"sourceFrame": 12, "timestampSeconds": 0.4, "keptIndex": 0}]
            sheets = make_contact_sheets([frame], rows, [3], root)
            archive = make_unique_frame_archive([frame], rows, root)
            self.assertEqual(1, len(sheets))
            self.assertGreater(sheets[0].stat().st_size, 0)
            self.assertGreater(archive.stat().st_size, 0)

    def test_synthetic_video_decodes_into_contact_sheet_pipeline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            decoded = root / "decoded"
            output = root / "output"
            source.mkdir()
            decoded.mkdir()
            output.mkdir()
            for index, x in enumerate((8, 8, 42)):
                image = Image.new("RGB", (96, 64), "black")
                ImageDraw.Draw(image).rectangle((x, 12, x + 24, 48), fill="white")
                image.save(source / f"frame_{index:03d}.png")
            video = root / "test.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-framerate", "1",
                "-i", str(source / "frame_%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(video),
            ], check=True)
            probe = probe_video(video)
            extract_frames(video, decoded)
            paths = sorted(decoded.glob("frame_*.png"))
            self.assertEqual(3, len(paths))
            kept, manifest, counts = choose_unique_frames(paths, mode="perceptual", threshold=6, fps=1.0)
            rows = [row for row in manifest if row["keptIndex"] is not None]
            sheets = make_contact_sheets(kept, rows, counts, output)
            self.assertEqual("1/1", probe["avg_frame_rate"])
            self.assertEqual(2, len(kept))
            self.assertEqual(1, len(sheets))

    @mock.patch("service.socket.getaddrinfo")
    def test_source_url_requires_approved_public_https_host(self, lookup):
        lookup.return_value = [(None, None, None, None, ("8.8.8.8", 443))]
        self.assertEqual(
            "https://files.oaiusercontent.com/video.mp4",
            validate_source_url("https://files.oaiusercontent.com/video.mp4"),
        )
        with self.assertRaises(ValueError):
            validate_source_url("http://files.oaiusercontent.com/video.mp4")
        with self.assertRaises(ValueError):
            validate_source_url("https://evil.example/video.mp4")

    @mock.patch("service.socket.getaddrinfo")
    def test_source_url_rejects_private_resolution(self, lookup):
        lookup.return_value = [(None, None, None, None, ("127.0.0.1", 443))]
        with self.assertRaises(ValueError):
            validate_source_url("https://files.oaiusercontent.com/video.mp4")


if __name__ == "__main__":
    unittest.main()
