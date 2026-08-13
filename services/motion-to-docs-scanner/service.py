import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from google.cloud import storage
from PIL import Image, ImageDraw, ImageFont
import imagehash

app = Flask(__name__)
storage_client = storage.Client()
OUTPUT_BUCKET = os.environ["MOTION_SCANNER_BUCKET"]
MAX_VIDEO_BYTES = int(os.environ.get("MAX_VIDEO_BYTES", str(512 * 1024 * 1024)))


def download_video(url: str, target: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "HomeCenter-MotionScanner/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_VIDEO_BYTES:
                raise ValueError("video exceeds configured size limit")
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def probe_video(video: Path) -> dict:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate,nb_frames,duration,width,height",
        "-of", "json", str(video)
    ], text=True)
    return json.loads(raw)["streams"][0]


def extract_frames(video: Path, frames_dir: Path) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vsync", "0", str(frames_dir / "frame_%09d.png")
    ], check=True)


def hamming(a, b) -> int:
    return a - b


def choose_unique_frames(frame_paths, threshold: int) -> tuple[list, list]:
    kept = []
    manifest = []
    hashes = []
    duplicate_counts = []
    for source_index, path in enumerate(frame_paths):
        with Image.open(path) as image:
            fingerprint = imagehash.phash(image.convert("RGB"), hash_size=16)
        nearest_index = None
        nearest_distance = None
        for index, prior in enumerate(hashes):
            distance = hamming(fingerprint, prior)
            if nearest_distance is None or distance < nearest_distance:
                nearest_index, nearest_distance = index, distance
                if distance == 0:
                    break
        if nearest_distance is None or nearest_distance > threshold:
            kept_index = len(kept)
            kept.append(path)
            hashes.append(fingerprint)
            duplicate_counts.append(0)
            manifest.append({
                "sourceFrame": source_index,
                "keptIndex": kept_index,
                "perceptualHash": str(fingerprint),
                "nearestDistance": nearest_distance,
                "duplicateOf": None,
            })
        else:
            duplicate_counts[nearest_index] += 1
            manifest.append({
                "sourceFrame": source_index,
                "keptIndex": None,
                "perceptualHash": str(fingerprint),
                "nearestDistance": nearest_distance,
                "duplicateOf": nearest_index,
            })
    return kept, manifest, duplicate_counts


def make_contact_sheets(kept, duplicate_counts, output_dir: Path, columns=4, rows=4):
    sheets = []
    per_sheet = columns * rows
    thumb_w, thumb_h, label_h = 480, 270, 34
    for sheet_index in range(0, len(kept), per_sheet):
        batch = kept[sheet_index:sheet_index + per_sheet]
        canvas = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + label_h)), "white")
        draw = ImageDraw.Draw(canvas)
        for local_index, path in enumerate(batch):
            kept_index = sheet_index + local_index
            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((thumb_w, thumb_h))
                x = (local_index % columns) * thumb_w + (thumb_w - image.width) // 2
                y = (local_index // columns) * (thumb_h + label_h)
                canvas.paste(image, (x, y))
            draw.text(
                ((local_index % columns) * thumb_w + 8, y + thumb_h + 7),
                f"Unique {kept_index:05d} | collapsed {duplicate_counts[kept_index]} duplicates",
                fill="black",
            )
        sheet_path = output_dir / f"contact_sheet_{sheet_index // per_sheet:04d}.jpg"
        canvas.save(sheet_path, "JPEG", quality=92, optimize=True)
        sheets.append(sheet_path)
    return sheets


def upload_file(path: Path, object_name: str, content_type: str) -> dict:
    blob = storage_client.bucket(OUTPUT_BUCKET).blob(object_name)
    blob.upload_from_filename(path, content_type=content_type)
    blob.reload()
    return {
        "bucket": OUTPUT_BUCKET,
        "object": object_name,
        "generation": str(blob.generation),
        "size": int(blob.size),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


@app.post("/scan")
def scan():
    payload = request.get_json(force=True)
    source_url = payload.get("sourceUrl")
    if not source_url:
        return jsonify(error="sourceUrl is required"), 400
    threshold = int(payload.get("distanceThreshold", 6))
    if threshold < 0 or threshold > 64:
        return jsonify(error="distanceThreshold must be between 0 and 64"), 400
    scan_id = payload.get("scanId") or str(uuid.uuid4())
    with tempfile.TemporaryDirectory(prefix="motion-scan-") as temp:
        root = Path(temp)
        frames_dir = root / "frames"
        output_dir = root / "output"
        frames_dir.mkdir()
        output_dir.mkdir()
        video = root / "source.video"
        source_sha256 = download_video(source_url, video)
        probe = probe_video(video)
        extract_frames(video, frames_dir)
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        kept, manifest_rows, duplicate_counts = choose_unique_frames(frame_paths, threshold)
        sheets = make_contact_sheets(kept, duplicate_counts, output_dir)
        manifest = {
            "schema": "home-center.motion-to-docs.v1",
            "scanId": scan_id,
            "sourceSha256": source_sha256,
            "mode": "perceptual",
            "distanceThreshold": threshold,
            "video": probe,
            "totalFrames": len(frame_paths),
            "uniqueFrames": len(kept),
            "duplicateFrames": len(frame_paths) - len(kept),
            "frames": manifest_rows,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        prefix = f"motion-scans/{scan_id}"
        artifacts = [upload_file(manifest_path, f"{prefix}/manifest.json", "application/json")]
        for path in sheets:
            artifacts.append(upload_file(path, f"{prefix}/{path.name}", "image/jpeg"))
        return jsonify({**manifest, "artifacts": artifacts})


@app.get("/health")
def health():
    return jsonify(ok=True, service="motion-to-docs-scanner", version="0.1.0")
