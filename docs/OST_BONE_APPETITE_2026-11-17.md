# Bone Appetite — One-Hour OST Production Receipt
Date: 2026-11-17
Procedure: [OST Etiquette](OST_ETIQUETTE.md). User supplied title, seven audio files and exact cover.
## Outputs and QA
- Bone_Appetite_One_Hour_1080p.mp4: 129868009 bytes, SHA-256 4c833873496d4f07d0ea22b12ce151cca523f6647b3dd3fcf9ba2d6b007b396e. H.264 1920x1080, 1 fps, 3600 seconds; MP3 stereo 44.1 kHz, 3600.013991 s with codec padding.
- Bone_Appetite_One_Hour_OST.mp3: 115202132 bytes, SHA-256 0cede2f80527275bd25fa3b7d52fc4a1f526be6a6c56d41c19ba8c5f0b0a857b, 256 kbps, 3600.039184 s including padding. Audio packet SHA-256 matches both files: 1f4bce27bb721d7c5cbc6b11b23fcb9f4a22676b68fd9d09e0efe1d58e1099cb.
- Cover 957.png SHA-256 40e01ebd3ad530f564408c2ba0ca5563c6661f5d1eb7ef558692823b86dd9393; exact supplied artwork scaled to 1920x1080 by Lanczos. Frame comparison at 5, 1800, 3599 seconds: mean RGB absolute error 1.805, 1.807, 1.805 on 0–255 scale.
## Inventory
Seven inputs, six distinct hashes and three filename title families.
| File | SHA-256 | Usable seconds |
|---|---|---:|
| The_Marionette's_Revolt.mp3 | 22b95bd8650a39a2c02fc92ecf55587a4fd899601b571d34f5eeeb3ea74900ac | 205.45 |
| The_Marionette's_Revolt(1).mp3 | same as unnumbered | duplicate |
| The_Carnival_Bites_Back(1).mp3 | d415a1805cf518efa1fd7b13d4b2cbe68c542eee041de8b8c3fc71130d9cd8a4 | 223.50 |
| The_Carnival_Bites_Back(2).mp3 | c3a7be8d9ead8791b42abdec12f5c90b776b9327c1c0c10964db945508168878 | 204.75 |
| The_Skeleton_Ball.mp3 | 8d08a472b55a889226dd7445622dee2ca74868bc238feaa0e3a2ee85b4a1ce50 | 196.55 |
| The_Skeleton_Ball(1).mp3 | 256c16577058ca8821edb744d50240d9c3018d6fba633d842f9dae1dfd454dd2 | 195.95 |
| The_Skeleton_Ball(2).mp3 | 260a58f3b19c680d92c82a97f39652e5ce4b1c05a503c5478d017505d187a077 | 194.60 |
## Method
Three varied passes through six recordings; no adjacent filename title families match. Decoded 44.1 kHz float stereo, trimmed near-silent edges using 50 ms RMS threshold 0.002 with one-window margin. Attenuation to median source RMS, 17 equal-power overlaps about 3.670588 s, exactly 158760000 stereo sample frames, global gain 0.7592641223, final sample peak 0.88, RMS 0.17085162. Minimum 100 ms transition RMS 0.01942189; all windows non-silent by automated check. First MP3 encode timed out; retried successfully using libmp3lame compression level 7 at 256 kbps. Repeated a 300-second static video segment by stream copy and copied encoded audio without re-encoding. Subjective listening and beat/key matching not independently performed.
## Chapters
00:00:00 The Skeleton Ball (take 2)
00:03:11 The Marionette's Revolt
00:06:33 The Skeleton Ball (take 1)
00:09:45 The Carnival Bites Back (take 1)
00:13:25 The Skeleton Ball
00:16:38 The Carnival Bites Back (take 2)
00:19:59 The Skeleton Ball (take 1)
00:23:11 The Marionette's Revolt
00:26:33 The Skeleton Ball
00:29:46 The Carnival Bites Back (take 1)
00:33:26 The Skeleton Ball (take 2)
00:36:36 The Carnival Bites Back (take 2)
00:39:58 The Skeleton Ball
00:43:10 The Marionette's Revolt
00:46:32 The Carnival Bites Back (take 1)
00:50:12 The Skeleton Ball (take 1)
00:53:24 The Carnival Bites Back (take 2)
00:56:45 The Skeleton Ball (take 2)
## Evidence boundary
Conversation artifact delivery verified at file level; remote binary archival and owner playback not verified. This receipt is documentation only.
