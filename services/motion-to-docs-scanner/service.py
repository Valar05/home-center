import hashlib
import ipaddress
import json
import os
import socket
import subprocess
import tempfile
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import timedelta
from fractions import Fraction
from pathlib import Path

from flask import Flask, jsonify, request
from google.cloud import storage
from PIL import Image, ImageDraw

app = Flask(__name__)
OUTPUT_BUCKET = os.environ["MOTION_SCANNER_BUCKET"]
MAX_VIDEO_BYTES = int(os.environ.get("MAX_VIDEO_BYTES", str(512 * 1024 * 1024)))
MAX_DECODED_FRAMES = int(os.environ.get("MAX_DECODED_FRAMES", "50000"))
ALLOWED_SOURCE_HOST_SUFFIXES = tuple(
    value.strip().lower()
    for value in os.environ.get(
        "ALLOWED_SOURCE_HOST_SUFFIXES",
        "oaiusercontent.com,blob.core.windows.net,amazonaws.com,storage.googleapis.com,googleusercontent.com",
    ).split(",")
    if value.strip()
)
_storage_client = None


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _host_is_allowed(host: str) -> bool:
    host = host.rstrip(".").lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_SOURCE_HOST_SUFFIXES)


def validate_source_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("sourceUrl must be an HTTPS URL on an approved upload host")
    if not _host_is_allowed(parsed.hostname):
        raise ValueError("sourceUrl host is not approved")
    for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError("sourceUrl resolved to a non-public address")
    return url


class ApprovedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_video(url: str, target: Path) -> str:
    validate_source_url(url)
    digest = hashlib.sha256()
    total = 0
    req = urllib.request.Request(url, headers={"User-Agent": "HomeCenter-MotionScanner/1.0"})
    opener = urllib.request.build_opener(ApprovedRedirectHandler())
    with opener.open(req, timeout=120) as response, target.open("wb") as out:
        validate_source_url(response.geturl())
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
        "-of", "json", str(video),
    ], text=True)
    streams = json.loads(raw).get("streams", [])
    if not streams:
        raise ValueError("uploaded file has no video stream")
    return streams[0]


def extract_frames(video: Path, frames_dir: Path) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vsync", "0", str(frames_dir / "frame_%09d.png"),
    ], check=True)


def difference_hash(image: Image.Image) -> int:
    pixels = list(image.convert("L").resize((17, 16), Image.Resampling.LANCZOS).getdata())
    value = 0
    for row in range(16):
        offset = row * 17
        for column in range(16):
            value = (value << 1) | int(pixels[offset + column] > pixels[offset + column + 1])
    return value


def choose_unique_frames(frame_paths, mode: str, threshold: int, fps: float) -> tuple[list, list, list]:
    kept = []
    manifest = []
    fingerprints = []
    exact_index = {}
    duplicate_counts = []
    for source_index, path in enumerate(frame_paths):
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            if mode == "exact":
                fingerprint = hashlib.sha256(rgb.tobytes()).hexdigest()
            else:
                fingerprint = difference_hash(rgb)

        nearest_index = None
        nearest_distance = None
        if mode == "exact":
            nearest_index = exact_index.get(fingerprint)
            nearest_distance = 0 if nearest_index is not None else None
        else:
            for index, prior in enumerate(fingerprints):
                distance = (fingerprint ^ prior).bit_count()
                if nearest_distance is None or distance < nearest_distance:
                    nearest_index, nearest_distance = index, distance
                    if distance == 0:
                        break

        duplicate = nearest_index is not None and (mode == "exact" or nearest_distance <= threshold)
        hash_value = fingerprint if mode == "exact" else f"{fingerprint:064x}"
        if not duplicate:
            kept_index = len(kept)
            kept.append(path)
            fingerprints.append(fingerprint)
            if mode == "exact":
                exact_index[fingerprint] = kept_index
            duplicate_counts.append(0)
            manifest.append({
                "sourceFrame": source_index,
                "timestampSeconds": round(source_index / fps, 6),
                "keptIndex": kept_index,
                "hash": hash_value,
                "hashType": "sha256-rgb" if mode == "exact" else "dhash-256",
                "nearestDistance": nearest_distance,
                "duplicateOf": None,
            })
        else:
            duplicate_counts[nearest_index] += 1
            manifest.append({
                "sourceFrame": source_index,
                "timestampSeconds": round(source_index / fps, 6),
                "keptIndex": None,
                "hash": hash_value,
                "hashType": "sha256-rgb" if mode == "exact" else "dhash-256",
                "nearestDistance": nearest_distance,
                "duplicateOf": nearest_index,
            })
    return kept, manifest, duplicate_counts


def make_contact_sheets(kept, kept_rows, duplicate_counts, output_dir: Path, columns=4, rows=4):
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
            row = kept_rows[kept_index]
            draw.text(
                ((local_index % columns) * thumb_w + 8, y + thumb_h + 7),
                f"Frame {row['sourceFrame']:09d} | {row['timestampSeconds']:.3f}s | collapsed {duplicate_counts[kept_index]}",
                fill="black",
            )
        sheet_path = output_dir / f"contact_sheet_{sheet_index // per_sheet:04d}.jpg"
        canvas.save(sheet_path, "JPEG", quality=92, optimize=True)
        sheets.append(sheet_path)
    return sheets


def make_unique_frame_archive(kept, kept_rows, output_dir: Path) -> Path:
    archive = output_dir / "unique_frames.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for index, path in enumerate(kept):
            row = kept_rows[index]
            name = f"unique_{index:09d}_source_{row['sourceFrame']:09d}.png"
            bundle.write(path, arcname=name)
    return archive


def upload_file(path: Path, object_name: str, content_type: str) -> dict:
    blob = get_storage_client().bucket(OUTPUT_BUCKET).blob(object_name)
    blob.upload_from_filename(path, content_type=content_type)
    blob.reload()
    signed_url = blob.generate_signed_url(version="v4", expiration=timedelta(minutes=30), method="GET")
    return {
        "bucket": OUTPUT_BUCKET,
        "object": object_name,
        "generation": str(blob.generation),
        "size": int(blob.size),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "signedUrl": signed_url,
        "signedUrlExpiresMinutes": 30,
    }


@app.post("/scan")
def scan():
    try:
        payload = request.get_json(force=True)
        source_url = payload.get("sourceUrl")
        if not source_url:
            raise ValueError("sourceUrl is required")
        mode = payload.get("mode", "perceptual")
        if mode not in ("perceptual", "exact"):
            raise ValueError("mode must be perceptual or exact")
        threshold = int(payload.get("distanceThreshold", 6))
        if threshold < 0 or threshold > 64:
            raise ValueError("distanceThreshold must be between 0 and 64")
        if mode == "exact":
            threshold = 0
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
            if not frame_paths:
                raise ValueError("uploaded video decoded to zero frames")
            if len(frame_paths) > MAX_DECODED_FRAMES:
                raise ValueError("video exceeds configured decoded-frame limit")
            rate = Fraction(probe.get("avg_frame_rate") or "1/1")
            fps = float(rate) if rate else 1.0
            kept, manifest_rows, duplicate_counts = choose_unique_frames(frame_paths, mode, threshold, fps)
            kept_rows = [row for row in manifest_rows if row["keptIndex"] is not None]
            sheets = make_contact_sheets(kept, kept_rows, duplicate_counts, output_dir)
            archive = make_unique_frame_archive(kept, kept_rows, output_dir)
            manifest = {
                "schema": "home-center.motion-to-docs.v1",
                "scanId": scan_id,
                "sourceSha256": source_sha256,
                "mode": mode,
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
            artifacts = [
                upload_file(manifest_path, f"{prefix}/manifest.json", "application/json"),
                upload_file(archive, f"{prefix}/unique_frames.zip", "application/zip"),
            ]
            for path in sheets:
                artifacts.append(upload_file(path, f"{prefix}/{path.name}", "image/jpeg"))
            return jsonify({**manifest, "artifacts": artifacts})
    except (ValueError, urllib.error.URLError, subprocess.CalledProcessError) as error:
        return jsonify(error=str(error)), 400


@app.get("/health")
def health():
    return jsonify(ok=True, service="motion-to-docs-scanner", version="0.2.0")
