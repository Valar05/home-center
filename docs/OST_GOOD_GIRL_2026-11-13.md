# GOOD GIRL | One-Hour YouTube OST Production Record
**Date:** 2026-11-13  
**Authority:** owner supplied eight MP3 files and one 1536×864 image; owner confirmed the OST etiquette's **one-hour default**, and requested a YouTube-style video and a documentation update.  
**Scope:** exact supplied music and image, no newly generated material.

## Source files and provenance

All eight files are byte-distinct (different SHA-256), stereo 44,100 Hz. Durations are decoded sample counts, not the MP3 format header's padded duration.

| Source | Decoded duration (s) | SHA-256 |
|---|---:|---|
| `GOOD_GIRL.mp3` | 188.910 | `009298ce734ebc5797b222e440d2aea1299ea3bae8b7d91272bad8ff6c7ed1cf` |
| `GOOD_GIRL(1).mp3` | 172.590 | `a81b84e1db527f354e40b7cca7b36819dfaf0ffc0186aac038e88a7424f5351e` |
| `GOOD_GIRL(2).mp3` | 169.510 | `e4bd6ac7cf629c677cd4e14c67271667f723d3450642bbab06b092d498feedad` |
| `GOOD_GIRL(3).mp3` | 178.150 | `80a76abfd3c917a44ddc15b79804f9d72df8cba0ddecb1d4f1172c1373254c43` |
| `GOOD_GIRL(4).mp3` | 178.030 | `acc77860417792fb567f56e14753a62ae97a25bdf4c12e1337f34cd5c13121e9` |
| `GOOD_GIRL(5).mp3` | 177.470 | `9f3d701616e1855a91e15743f109bd39f3413d25c242d842e68e96d75bec8ad0` |
| `GOOD_GIRL(6).mp3` | 182.990 | `ba16b3b64e8dbe5d70162fb77ea0275777caaa5da16963c83e92fcde9a285e6a` |
| `GOOD_GIRL(7).mp3` | 180.910 | `c3931c215e579b020b414d8ec18780018c4607e576a9829e904b0b80858029ea` |

**Cover:** supplied `293.png`, 1536×864, exact 16:9; SHA-256 `2f7a874ee80d0ef2b12438d412f81cb625df3ee17a4363b4892a6aa58f971a13`. Scaled without cropping or inserted title.

## Program and transition math

- **21 placements** from eight originals; 20 crossfades of **346,692 samples = 7.8614966 seconds** each, at 44,100 Hz.
- Sum of all decoded placement durations = **3757.230068 seconds**. Removing 20 overlaps yields **3600.000136 seconds** of pre-encoding PCM.
- Decoded source samples were mixed as float32 stereo using quarter-sine/quarter-cosine **equal-power transitions**. Fixed per-input linear gain 0.78 preserves dynamics and headroom; final MP3 encoded once.
- The ordering is varied across repetitions; the same **file recording** never occurs twice in succession.
- **Composition-level exception:** all eight input filenames carry the one title `GOOD GIRL`. Avoiding adjacent instances of that named composition is impossible without adding music, which was not authorized. No unverified "different composition" claim is made.

## Verified YouTube chapter positions

These timestamps mark the start of each incoming recording's overlap window and are rounded down to whole seconds.

```text
00:00:00 GOOD GIRL | GOOD_GIRL.mp3
00:03:01 GOOD GIRL | GOOD_GIRL(1).mp3
00:05:45 GOOD GIRL | GOOD_GIRL(2).mp3
00:08:27 GOOD GIRL | GOOD_GIRL(3).mp3
00:11:17 GOOD GIRL | GOOD_GIRL(4).mp3
00:14:07 GOOD GIRL | GOOD_GIRL(5).mp3
00:16:57 GOOD GIRL | GOOD_GIRL(6).mp3
00:19:52 GOOD GIRL | GOOD_GIRL(7).mp3
00:22:45 GOOD GIRL | GOOD_GIRL(4).mp3
00:25:35 GOOD GIRL | GOOD_GIRL(2).mp3
00:28:17 GOOD GIRL | GOOD_GIRL(6).mp3
00:31:12 GOOD GIRL | GOOD_GIRL(1).mp3
00:33:57 GOOD GIRL | GOOD_GIRL(7).mp3
00:36:50 GOOD GIRL | GOOD_GIRL(3).mp3
00:39:40 GOOD GIRL | GOOD_GIRL(5).mp3
00:42:30 GOOD GIRL | GOOD_GIRL.mp3
00:45:31 GOOD GIRL | GOOD_GIRL(5).mp3
00:48:20 GOOD GIRL | GOOD_GIRL(1).mp3
00:51:05 GOOD GIRL | GOOD_GIRL(6).mp3
00:54:00 GOOD GIRL | GOOD_GIRL(3).mp3
00:56:51 GOOD GIRL | GOOD_GIRL.mp3
```

## Verified outputs

| Artifact | Properties | Byte count | SHA-256 |
|---|---|---:|---|
| `GOOD_GIRL_Seamless_One_Hour.mp3` | MP3 stereo 44.1 kHz 256 kb/s, ffprobe duration 3600.039184 s | 115202132 | `af3ea0785d83434167221d74cebc15bcbf92f2ceba01ec2e128146415e796158` |
| `GOOD_GIRL_One_Hour_1080p.mp4` | H.264 1920×1080 1 fps, yuv420p; AAC stereo 44.1 kHz; both streams 3600.000000 s | 246463051 | `553b4dfac750a49924be5bea3594b35ebd1dc9f29bb0e16ceb7ba956682fed3f` |

**Automated QA:** 8/8 byte-unique inputs; all 21 placements accounted for; zero adjacent identical recordings; RMS checks around all 20 transitions found no 0.5-second zeros/silent insertion; audio MP3 and MP4 video/audio stream durations probed successfully. The source image's 16:9 aspect was preserved.  
**Audition caveat:** manual listening quality review of all junctions was **not performed**, so artistic smoothness is not independently certified.  
**Delivery-status distinction:** actual files were rendered in the ChatGPT session and offered by direct artifact links. This GitHub document is the durable Home Center evidence record. **An independent durable upload of the binary MP4/audio to Home Center storage is not verified by this record.**

## Corrective procedure note

When a user requests a YouTube soundtrack video under OST etiquette without restating runtime, use the **one-hour standard**. Do not substitute a single-pass video. Verify the MP4's full-length audio and video streams before calling the video produced. Keep file hashes and the exact ordered chapter map, rather than describing a locally rendered file as a durable remote binary.
