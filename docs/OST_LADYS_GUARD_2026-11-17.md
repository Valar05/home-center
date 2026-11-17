# Lady's Guard — One-Hour OST Production Receipt
Date: 2026-11-17
Procedure: [OST Etiquette v1.1](OST_ETIQUETTE.md), readback SHA f9e43db59bbd9165d5898294a26f83b274277ab5.
## Verified outputs
- Ladys_Guard_One_Hour_1080p.mp4: 105337076 bytes, 3600.000 s, H.264 1920×1080 1 fps, AAC-LC stereo 44.1 kHz. SHA-256 6e5f946cc1482534c27d250b2d4cd4836b1f51ad47cb180424248de547592958.
- Ladys_Guard_One_Hour_OST.m4a: 87387690 bytes, 3600.000 s, AAC stereo 44.1 kHz, target 192 kbps. SHA-256 c69ce874ac5eef9c1f2d5a25aa15b87225884b1861a48143a8c4c16f4b6c93c0.
- Identical encoded audio packet stream in both: SHA-256 1f89e8fa41889a66a8659c6e0c7ca1e8c29834e6d3bfa8a197f7de6d2b412d32.
- Exact supplied cover 870.png SHA-256 7c3fc3ab0a4ac4edf4cbaf704b7599e3bc9544870e237bcd46a1f175bd9e48af; 1536×864 scaled to 1920×1080 without cropping; decoded video frames at 5, 1800 and 3595 s compared against scaled original, mean RGB absolute differences ~2.02/255.
## Inputs
Eight distinct file hashes, three filename title families. Musical identity beyond filename grouping not independently established.
| Source | SHA-256 | Usable seconds |
|---|---|---:|
| La_Chanson_de_Gauvain(1).mp3 | 4e06b13e230cdc4e18d15e7d1846009340988e0d662ac07c3e1cc34a294fe0fc | 207.75 |
| La_Chanson_de_Gauvain.mp3 | 89f0fe03ebdfb583b7007744550523ea507ac27b0c6a7665e332fdb7201b108e | 208.30 |
| La_Chevauchée_des_Preux(1).mp3 | 6b2e7faeacc019c3663d28ab232220c8678ceba1cfd280c40c748539191f7120 | 186.75 |
| La_Chevauchée_des_Preux.mp3 | 7a4939e1fc0f3caaee7b46326aff7bfaa83c690faa3205822e8949e48c93ea77 | 197.45 |
| The_Gallant_Hart(1).mp3 | 4d4b534d032e450a7818710fe77ee618ac53173475581c08e70d03b80157a51b | 197.30 |
| The_Gallant_Hart(2).mp3 | 7ef18080cef2420a71bb35379d333dd31a0d9d6b0c14a67c99de9be86cd66270 | 200.30 |
| The_Gallant_Hart(3).mp3 | f28baa930a9cad7fb8b0152a5bdd3604ff0e80a6eba2bc9056eafac04dbe92c9 | 192.15 |
| The_Gallant_Hart.mp3 | d11d82b9377b663552f147e2c71dfeeb3d920ab80ba0e5895feefa7c4737e222 | 169.25 |
## Method and QA
Two differently ordered complete passes of eight files and three additional placements, totaling 19. Adjacent filename families differ; all eight used. Decoded to 44.1 kHz stereo float, conservatively removed near-silent edges using 50ms RMS windows (threshold 0.002 with one-window margin), attenuated sources louder than median RMS and applied global gain 0.7194574099352105 for a master sample peak of 0.9; master RMS 0.1445610694. 18 sample-exact equal-power overlaps of 6.4666667 s, 158760000 frames (3600 s), 0.5 s opening fade and 2 s closing fade. Minimum 100 ms blended-transition RMS after global gain 0.00974156. Automated checks passed, subjective audition and beat/key alignment not independently verified. Initial MP3 encode timed out; discarded partial file and successfully encoded AAC with fast coder. Static video encoded as a 300 s H.264 segment repeated by stream copy. AAC master copied into MP4 and packet hash matched. No new music or generated visuals.
## Chapters
00:00:00 The Gallant Hart (take 1)
00:03:11 La Chevauchée des Preux
00:06:22 The Gallant Hart (take 2)
00:09:36 La Chanson de Gauvain (take 1)
00:12:57 The Gallant Hart
00:15:40 La Chanson de Gauvain
00:19:02 The Gallant Hart (take 3)
00:22:07 La Chevauchée des Preux (take 1)
00:25:08 La Chanson de Gauvain (take 1)
00:28:29 The Gallant Hart
00:31:12 La Chanson de Gauvain
00:34:33 The Gallant Hart (take 2)
00:37:47 La Chevauchée des Preux
00:40:58 The Gallant Hart (take 3)
00:44:04 La Chevauchée des Preux (take 1)
00:47:04 The Gallant Hart (take 1)
00:50:15 La Chanson de Gauvain
00:53:37 La Chevauchée des Preux
00:56:48 The Gallant Hart (take 3)
## Evidence boundary
Binary files rendered and verified in conversation artifact runtime and delivered through download links. Remote binary archival and actual owner playback not verified. This receipt is not a claim of remote binary upload.
