"""Finalize Pocket TTS streaming WAV headers for saved files, without touching PCM.

Pocket's streaming encoder intentionally advertises a 2,000,000,000-byte
data chunk before it knows the final length. Valid for streaming consumers;
not suitable for persisted WAV playback. This module only fixes that known
placeholder layout. The real-time HTTP stream is left untouched.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import struct


STREAM_DATA_PLACEHOLDER = 2_000_000_000
STREAM_RIFF_PLACEHOLDER = STREAM_DATA_PLACEHOLDER + 36


def finalize_wav_bytes(data: bytes) -> bytes:
    """Return WAV data with corrected size fields when the known sentinel occurs.

    All samples and all non-size header bytes remain byte-for-byte unchanged.
    Unexpected WAV layouts are passed through untouched, never guessed.
    """
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return data
    if data[12:16] != b"fmt " or struct.unpack_from("<I", data, 16)[0] != 16:
        return data
    if data[36:40] != b"data":
        return data
    riff_size = struct.unpack_from("<I", data, 4)[0]
    data_size = struct.unpack_from("<I", data, 40)[0]
    if riff_size != STREAM_RIFF_PLACEHOLDER or data_size != STREAM_DATA_PLACEHOLDER:
        return data
    fmt, channels, rate, byte_rate, block_align, bit_depth = struct.unpack_from(
        "<HHIIHH", data, 20
    )
    actual_data_size = len(data) - 44
    if (
        fmt != 1
        or channels < 1
        or rate <= 0
        or block_align != channels * ((bit_depth + 7) // 8)
        or byte_rate != rate * block_align
        or actual_data_size <= 0
        or actual_data_size % block_align != 0
        or actual_data_size >= 0xFFFFFFFF - 36
    ):
        raise ValueError("Pocket streaming WAV has an invalid PCM layout")
    result = bytearray(data)
    struct.pack_into("<I", result, 4, len(data) - 8)
    struct.pack_into("<I", result, 40, actual_data_size)
    return bytes(result)


def finalize_wav_file(source: Path, output: Path) -> Path:
    """Write corrected playable copy. Never overwrite the source."""
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise FileExistsError("Choose a new output path; source must be preserved")
    src = source.read_bytes()
    fixed = finalize_wav_bytes(src)
    with output.open("xb") as f:
        f.write(fixed)
        f.flush()
        os.fsync(f.fileno())
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(finalize_wav_file(args.source, args.output))


if __name__ == "__main__":
    main()
