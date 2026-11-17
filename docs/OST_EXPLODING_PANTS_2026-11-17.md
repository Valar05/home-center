# Exploding Pants — One-Hour OST Production Receipt
Date: 2026-11-17
Procedure: [OST Etiquette v1.1](OST_ETIQUETTE.md), readback SHA f9e43db59bbd9165d5898294a26f83b274277ab5.
## Verified output
- Exploding_Pants_One_Hour_YouTube_1080p.mp4: 274603390 bytes, 3600.013991 s container, 3600 s H.264 video at 1920×1080 1 fps, MP3 stereo 44.1 kHz. SHA-256 60b351ded92b956ccfddbf59bd22a1275b5a9b5488dcccee43ff5d3d86919e61.
- Exploding_Pants_One_Hour_OST_Audio.mp3: 115202132 bytes, 3600.039184 s (codec padding), MP3 256 kbps stereo 44.1 kHz. SHA-256 139716715ed1d271a83fa7d1f8c79e374a10cb0143793040f252c97a3e3d966c.
- Audio packet stream hash matches in both: 75f97fe7596850af266f1e2a014ce1db6fbd87628522e07fe4b8c833513d9b8f.
- Cover: supplied 852.png, 1536×864, Lanczos scaled to 1920×1080, no cropping or regeneration. Decoded frames at 5, 1800, 3595 s matched source (mean RGB absolute differences 4.020, 4.035, 4.022 on 0–255 scale).
## Inventory
Eight supplied MP3s, seven unique hashes, four title families; numbered Anvil Chorus file duplicates unnumbered file byte-for-byte.
| Source | SHA-256 | Usable decoded duration, seconds |
|---|---|---:|
| The_Clockwork_Collapse.mp3 | 0c4a3f515699a084f9d048c0265be3986e3584e877a87b0c5461034ecddc0425 | 208.95 |
| The_Clockwork_Collapse(1).mp3 | fcc2eaa20d46adb840de26e7d8051bda8ff96ac26de276afb0c84bdfeaf828a2 | 217.35 |
| Steam_&_Soot_Serenade.mp3 | 812be16e743cf57b8711eaa80f3840b3b41a3517483aed170967ecb029bbc1c9 | 187.20 |
| Steam_&_Soot_Serenade(1).mp3 | a4edb8c9ac319091ac9a4c4ad0ddb6f98462bbed8ef79dfd01be2d5f9ae2f376 | 210.45 |
| Wrench_&_Bustle.mp3 | ebd6f3064dbda15842e58e76a79cf2c96282fd425aa8b723950eb1de423786f3 | 223.60 |
| Wrench_&_Bustle(1).mp3 | 8cbdc5219f9ef0af1c2563fed537ccc60591c415781f04aab2c180625dd3573d | 204.00 |
| The_Anvil_Chorus_of_Bad_Ideas.mp3 | a0ec6bbf301c0cebe98965ffe0d86dbf68053df2ef9120b9d0228ab7028f3ec9 | 227.45 |
| The_Anvil_Chorus_of_Bad_Ideas(1).mp3 | same as unnumbered | duplicate |
## Method and QA
Decoded 44.1 kHz float stereo, conservatively trimmed near-silent edges using 50 ms RMS windows (threshold 0.002, one-window margin). Seventeen placements, sixteen equal-power sine/cosine crossfades, 4.259365–4.259388 s per transition; exactly 158760000 stereo sample frames before encoding. Attenuated above-median RMS recordings only, then applied global gain 0.795687454 to achieve maximum pre-encode sample magnitude 0.85. Sequence varied, every unique file used and no adjacent titles match. Minimum pre-global-gain 100 ms RMS across all transition windows 0.028874 (not silent). Full subjective audition and beat matching are unverified.
AAC encoding timed out twice; completed single MP3 encode at 256 kbps, copied without audio re-encoding into MP4. Static cover encoded as a 300-second H.264 segment, repeated twelve times by stream copy. Output checks and audio packet hash passed. This is a completed downloadable conversation artifact, not a verified remote binary ingest. The partial AAC file is not a deliverable.
## Chapters
00:00:00 Wrench & Bustle
00:03:39 Steam & Soot Serenade (alternate take)
00:07:06 The Anvil Chorus of Bad Ideas
00:10:49 The Clockwork Collapse (alternate take)
00:14:22 Wrench & Bustle (alternate take)
00:17:42 The Anvil Chorus of Bad Ideas
00:21:25 The Clockwork Collapse
00:24:49 Steam & Soot Serenade (alternate take)
00:28:16 The Clockwork Collapse (alternate take)
00:31:49 Wrench & Bustle
00:35:28 Steam & Soot Serenade
00:38:31 The Anvil Chorus of Bad Ideas
00:42:14 Steam & Soot Serenade (alternate take)
00:45:40 Wrench & Bustle (alternate take)
00:49:00 The Clockwork Collapse (alternate take)
00:52:33 The Anvil Chorus of Bad Ideas
00:56:16 Wrench & Bustle
## Evidence boundary
The production receipt documents actual rendered artifact metadata and source provenance; it does not prove binary persistence outside the conversation or owner playback.
