# Velvet Protocol: After Hours — One-Hour OST Production Receipt
**Date:** 2026-11-16  
**Owner:** Drew Clarke  
**Procedure:** [OST Etiquette](OST_ETIQUETTE.md), v1.1  
**Scope:** One-hour seamless arrangement of the nine user-provided MP3s, using the exact user-provided 16:9 cover `762.png` and a downloadable 1080p MP4.

## Delivery state
**Created and verified in the conversation artifact surface, not independently uploaded to Drive:**  
- Video: `Velvet_Protocol_After_Hours_One_Hour_YouTube_1080p.mp4`, 134,588,065 bytes, 3600.000 s, H.264, 1920×1080, 1 fps static image, AAC-LC stereo 44.1 kHz. SHA-256 `6a30cd832c138090067f1585c84daabccab8374270185ad34378015fc7d381aa`.
- Audio: `Velvet_Protocol_After_Hours_One_Hour_OST_Audio.m4a`, 120,404,865 bytes, 3600.000 s, AAC stereo 44.1 kHz. SHA-256 `404217bc56862080f330ed263afe46ee3fcc50dd046fc652d9085341d15a20c1`.
- Optional MP3: `Velvet_Protocol_After_Hours_One_Hour_OST_Audio.mp3`, 115,202,132 bytes, 3600.039 s due to MP3 codec padding, 256 kbps stereo. SHA-256 `398fb660dd8a58d6c796d24847288c51c26f0238dbf1ae7728f8fbb48b5cd777`.
- Cover: `762.png`, source 1536×864, extended without cropping only by direct scale to 1920×1080; SHA-256 `503de4837cd0ec9fd9a775d9d9dd4a25228400479a9342e1c438d3ec2a552eaf`.
- The video artwork was checked at 00:00:05, 00:30:00 and 00:59:55 against the supplied image; mean RGB absolute difference ~3.77/255 from compression/scaling. No altered characters, text, or generated replacement imagery.

## Input inventory and duplicates
Nine uploads, **seven unique recordings**, **four different composition families**. Original uploads remain unmodified.

| Supplied MP3 | Duration (s) | SHA-256 |
|---|---:|---|
| Velvet_Surveillance(1).mp3 | 209.188571 | `7c15c39f09ccc49d8f65ffc46eea417390db39947263263484af8df8e5a85533` |
| Velvet_Surveillance.mp3 | 187.350204 | `8c23cc2f2dc49e94d78dd67ad71ea017b5f9633c611b7fdccbc993956b83b183` |
| Velvet_Access(3).mp3 | 192.705306 | `2bc8efa1e5abac72ed6057a46cba3d4b7e1bf7a1ba831d2669b1b772f7d2963b` |
| Velvet_Access(2).mp3 | 192.705306 | Exact copy of (3) |
| Velvet_Access(1).mp3 | 192.705306 | Exact copy of (3) |
| Velvet_Access.mp3 | 189.910204 | `fc2a88fe28b1efc0b4eaa6de8713740b4bf0a9f01cbea1f684d0411941681520` |
| Velvet_Override.mp3 | 204.146939 | `f661be90946816e5d04112334821dc18e24ee50020097c4ad755fc0c2ac5ddfe` |
| Velvet_Blackout(1).mp3 | 194.351020 | `7e41b63ba1946330ef9ad80d8fd9ef9987f375bf5b48f0f8d4a650bdc27303b8` |
| Velvet_Blackout.mp3 | 183.040000 | `dcc48fb59e6a79d3047f7569cd47600fc7cec4d9a8957186f36914bc9092a3a8` |

## Mix math and method
19 source placements total **3725.17 seconds**. 18 transitions each **~6.953889 seconds**; overlap totals **125.17 seconds**. Exactly `3,600.000` seconds (158,760,000 frames at 44.1 kHz) of floating-point stereo audio produced. Crossfades use cosine/sine equal-power envelopes. All sources are preserved apart from overlap blends and a uniform final encoder safety gain of 0.856645514 to keep sample peaks below 0 dBFS. No per-track dynamics crushing or new music introduced. Rendered AAC and MP3 once from the floating-point master.

**Automated QA:** no consecutive placements share the same composition title; 18 crossfade midpoint windows have RMS at least 0.0717 (well above 0.003 silent-gap threshold). Independent listening at all 18 transitions was **not** performed, so subjective musical seamlessness remains unverified. Stream and duration checks on the resulting MP4 passed; opening/midpoint/end frame tests passed.

## YouTube chapters
```text
00:00:00 Velvet Surveillance (alternate take)
00:03:22 Velvet Access
00:06:25 Velvet Blackout (alternate take)
00:09:32 Velvet Override
00:12:50 Velvet Access (alternate take)
00:15:55 Velvet Surveillance
00:18:56 Velvet Override
00:22:13 Velvet Blackout
00:25:09 Velvet Surveillance (alternate take)
00:28:31 Velvet Access (alternate take)
00:31:37 Velvet Blackout (alternate take)
00:34:44 Velvet Override
00:38:01 Velvet Surveillance
00:41:02 Velvet Blackout (alternate take)
00:44:09 Velvet Access
00:47:12 Velvet Override
00:50:29 Velvet Blackout
00:53:25 Velvet Access (alternate take)
00:56:31 Velvet Surveillance (alternate take)
```

**Evidence limitation:** This repository document is a durable production receipt but does **not** establish the binary MP4 is stored in Home Center or Drive. The MP4, audio files, chapter text, and JSON manifest were created in the conversation artifact runtime and offered through verified download links; separate remote binary-ingest verification would be necessary to claim cloud persistence.
