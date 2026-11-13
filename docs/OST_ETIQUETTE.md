# OST Etiquette
**Version:** 1.0 · **Created:** 2026-11-13 · **Owner:** Drew Clarke  
**Purpose:** A repeatable, evidence-driven procedure for turning a small collection of instrumental soundtrack recordings into a continuous, long-form OST, then optionally pairing it with exact supplied cover art for YouTube.  
**Reference production:** *Blue Eyes, Crimson Jewels* (one-hour seamless mix, 2026-11-13).

> **Truth boundary:** Sections labeled **verified** come from the actual surviving audio, chapter file, image, or MP4. The editorial process and suggested crossfade implementation are a **reproducible procedure**, not a claim that the original, unpreserved generation script has been recovered.

## 1. Mission boundary and artist authority

1. Preserve the user's **specific requested songs and source takes**. Do not generate new music, replace audio, remix instruments, or substitute a different artwork unless explicitly commissioned.
2. "Arrangement" may mean **multiple distinct songs**, not one extended song. Ask only if truly ambiguous; otherwise respect the established meaning.
3. A **continuous mix** is one playable recording with overlapping transitions, not a playlist with silent gaps.
4. Repetition is allowed when the available material cannot fill the target runtime. **Never put the same composition back to back**, even if the two files are different takes. Change the order between repetitions and distribute recurring pieces through the program.
5. Never describe a copied file as an "alternate take" without verifying that its audio differs. Preserve originals and file hashes.
6. The user chooses the runtime and visual. A static-image soundtrack video must use the **exact attached image** and **exact specified mix**: no opportunistic redesign.
7. Deliver the actual requested artifact through the authorized surface with verification, a direct accessible link, and human-readable evidence. An attractive preview, source path, or plan is not the artifact.

## 2. Reference production: verified source inventory

Six MP3s were supplied, but there were **five unique recordings**. Durations below are from the mounted originals inspected with ffprobe; identifiers are SHA-256 of the source files.

| Input | Duration (seconds) | Relationship | SHA-256 |
|---|---:|---|---|
| `Blue_Eyes,_Crimson_Jewels(1).mp3` | 179.800816 | Main recording | `5cf573b54d2a044d16edd15bd97d6e57766831c7a559cd706a691ee319891e02` |
| `Blue_Eyes,_Crimson_Jewels(2).mp3` | 179.800816 | **Exact byte-for-byte duplicate** of (1), not another musical take | `5cf573b54d2a044d16edd15bd97d6e57766831c7a559cd706a691ee319891e02` |
| `Crimson_Valse.mp3` | 191.817143 | Original take | `46827559db075ec0f3b3e1eb09cd671f9c4141b801320fca26b39cdee662b279` |
| `Crimson_Valse(1).mp3` | 242.703673 | Distinct longer take | `8b13448bdda7c85df162ef9de819ed66f172de4ad896d3b2a9e980f8f2d840b3` |
| `Dangerous_Tenderness.mp3` | 198.896327 | Original take | `5464eace079d416dca0d77dfa17efa5b6d9399caec718f827af603db72007f34` |
| `Dangerous_Tenderness(1).mp3` | 214.517551 | Distinct longer take | `194678a201b45749ac94e5dcb972221557da0d20b60eb2ff1527edeb5e791568` |

**Verified finished mix:** `Blue_Eyes_Crimson_Jewels_Seamless_One_Hour.mp3`, duration **3600.039184 s**, stereo **44,100 Hz**, **256 kb/s** MP3, **115,202,132 bytes**, SHA-256 `248fe0bdbdb5af92619e4f502684b1404e10e3335e471d02407aed69e8fb6681`.

## 3. Reference sequence: the 18 placements

This is the actual sequence recorded in the surviving chapter sheet. Chapter stamps are rounded to seconds. "Blue Eyes" refers to the one unique audio recording, despite the chapter sheet's historical "alternate take" wording.

| # | Start | Composition / take |
|---:|---|---|
| 01 | 00:00 | Blue Eyes, Crimson Jewels |
| 02 | 02:52 | Crimson Valse (longer take) |
| 03 | 06:48 | Dangerous Tenderness (original) |
| 04 | 10:00 | Crimson Valse (original) |
| 05 | 13:04 | Dangerous Tenderness (longer take) |
| 06 | 16:32 | Crimson Valse (longer take) |
| 07 | 20:28 | Dangerous Tenderness (original) |
| 08 | 23:39 | Blue Eyes, Crimson Jewels |
| 09 | 26:32 | Dangerous Tenderness (longer take) |
| 10 | 30:00 | Crimson Valse (original) |
| 11 | 33:04 | Dangerous Tenderness (original) |
| 12 | 36:16 | Crimson Valse (longer take) |
| 13 | 40:12 | Dangerous Tenderness (longer take) |
| 14 | 43:39 | Blue Eyes, Crimson Jewels |
| 15 | 46:32 | Crimson Valse (original) |
| 16 | 49:37 | Dangerous Tenderness (longer take) |
| 17 | 53:04 | Crimson Valse (longer take) |
| 18 | 57:00 | Blue Eyes, Crimson Jewels |

**Verified assembly arithmetic:** The 18 selected source durations sum to **3,720.22857 s**. Seventeen transitions with **7.07 s** overlap each remove **120.19 s**, leaving **3,600.03857 s**. The encoded file's **3,600.039184 s** duration agrees to within a millisecond. This is the decisive evidence for the 18-placement, fixed-overlap reconstruction. The separate original mixing script and exact fade curves are **not recovered**.

## 4. Standard operating procedure

### A. Collect an explicit commission
Record: desired soundtrack or character/scene; exact supplied tracks/takes; target total runtime; repeats allowed or forbidden; consecutive-repeat exclusion; transition style; final audio format; visual asset, if any; video dimensions; final destination. For this reference: user specified an **hour-long arrangement of multiple songs**, **seamless blending**, repeats allowed **but never back to back**, and a YouTube MP4 with the chosen vampire cover art.

### B. Inventory and preserve
- Keep originals immutable; generate checksums, durations, sample rates, channel counts, and apparent silence at heads/tails.
- Deduplicate by SHA-256; musical identity is tracked independently of filename. Different filenames may be identical recordings.
- Group files by composition/title; distinguish truly alternate recordings within each group.
- Protect source identifiers in a manifest; never quietly swap in a regenerated take.
- Reject corrupt/empty inputs and document clipping or defects before mixing.

### C. Build the rotation
- Plan enough placements to cover the target duration **after overlaps**.
- At each next placement, exclude the immediately previous **composition**, not merely the previous filename. Prefer non-recent compositions where the library permits.
- Rotate genuine alternate takes for textural variation. Vary the ordering between cycles rather than cloning an identical album sequence several times.
- Listen for tonal, dynamic, rhythmic and phrase compatibility. Prefer transitions from a decaying tail to an incoming musical phrase; avoid colliding loud climaxes or cutting cadences at random.
- Preserve a satisfying **opening, middle, and finale**, including a natural closing song where feasible.
- Validate the composition adjacency invariant before rendering.

### D. Solve the exact target runtime
For `N` placements with source durations `d₁…dₙ` and transition overlap durations `x₁…xₙ₋₁`:

`total_seconds = sum(durations) - sum(overlaps)`.

For uniform overlap `x`: `x = (sum(durations) - target_seconds)/(N-1)`.

For the reference: `x = (3720.22857 - 3600)/17 = 7.072269… seconds`, rounded to **7.07 seconds**. This retained full source tracks and reached almost exactly one hour **without back-to-back repetition**.

If the resulting overlap is musically unsuitable, **change the sequence or use individually chosen overlaps**; do not blindly force fades of arbitrary length. Use a phrase-aware ending, a very small transparent timing correction, or a restrained final fade only when necessary. Do not silently pad with dead air.

### E. Render genuinely overlapping transitions
- Decode all sources to one consistent working format (typically 44.1 or 48 kHz stereo, floating point).
- Apply gain matching and check headroom before the mix. Preserve musical dynamics; do not automatically crush to an arbitrary target loudness.
- Overlap the outgoing final `x` seconds with the incoming first `x` seconds. Use a smooth energy-conscious fade, e.g. quarter-sine/equal-power, **as the recommended reproducible implementation**. The original fade curve is **unverified**.
- Render a continuous sample stream. No per-track silent insertions; no abrupt changes in stereo routing.
- Listen at every junction, especially 10 seconds on either side. Check for clicks, doubled percussion, phase issues, sudden loudness changes and inadvertent silence.
- Avoid re-encoding every intermediate join: compose in lossless/floating-point working audio and **encode only the final deliverable**.

### F. Export audio and chapters
- Default deliverable for this reference: stereo MP3, 44,100 Hz, 256 kbps, approximately 60:00.
- Verify output duration, channel count and bitrate with a decoder/metadata probe. Hash the final file.
- Calculate chapters from exact cumulative durations and overlaps, rounding each start to whole seconds for YouTube. Label recurring compositions accurately, and never invent distinct takes.
- Store the source manifest, sequence, overlaps, chapter sheet, output path, checksum, and any caveats.

### G. Create the optional cover-art MP4
- Only after the audio master is valid, use the **exact user-selected image**. Do not regenerate the scene or use a lookalike.
- Scale/aspect-fit to **1920×1080 (16:9)** without unintended cropping, distortion, or black bars. Preserve facial composition and key details.
- Hold the still image for the full audio duration, producing an actual **video stream plus audio stream**, not an image-only or audio-only file.
- Preferred broad-compatibility profile for future delivery: H.264, yuv420p, AAC stereo (e.g. 192–256 kbps), MP4 with fast-start metadata. A 24/30 fps encode is conventional; an economical low-frame-rate static encode is permissible where accepted.
- **Verified reference variant:** `Blue_Eyes_Crimson_Jewels_One_Hour_User_Background_1080p.mp4` used the user's image, H.264 1920×1080 **at 1 fps**, with the original **MP3 audio copied into the MP4** (not AAC); duration **3600.013991 s**, size **127,423,700 bytes**, SHA-256 `821cd6db9cd24739a26106bff32933146c14622a8d63efe3033d5cbb782f4638`. Distinguish these verified file facts from the recommended future profile.
- Reference image `185.png` SHA-256: `339ce60d56d7aa0b1a3117de491fe75bfa58cb70a373b9ecda9eb73afee8411a`. It is the user-supplied 16:9 vampire portrait with moonlit window and candles.

### H. Verify, deliver, and retain evidence
A completed OST handoff includes:
1. Actual playable file at the requested destination, not merely a command or a promise.
2. Verified duration and media streams; MP4 must contain both picture and sound throughout the full runtime.
3. Spot-checked opening, midpoint, last minute and **all transitions** for audible discontinuities; if listening was not performed, mark that particular QA **unverified** rather than claiming it.
4. Automatic adjacency check: no two neighboring segments share a composition ID.
5. An accurate chapter file and manifest, including original source hashes and final output hashes.
6. A direct downloadable link that points to the file **that was really created**; do not infer or fabricate sandbox paths.
7. Durable records through Home Center or an explicitly authorized repository/workspace. A ChatGPT local scratch file alone is not a durable user deliverable.

## 5. Reproduction algorithm (specification, not the lost original script)

```text
INPUT: immutable audio assets grouped by composition
       target_seconds, desired_transition_style, cover_art(optional)
inventory metadata and SHA-256
deduplicate identical assets
choose placements with:
    adjacent_composition_is_different
    repeated_cycles_change_order
    alternate_takes_are_real
    opening/middle/finale_are_coherent
choose overlaps so sum(duration)-sum(overlap) ~= target_seconds
standardize decoded audio working format
out = first song
for each remaining song:
    overlap last x seconds of out with first x seconds of song
    apply smooth out/in envelopes; preserve musical continuity
    append song material following its overlapped head
encode audio once; verify streams, runtime, chapter positions and checksum
if cover_art:
    encode exact image as continuous video for audio duration
    mux audio; verify both streams and mid/ending frames
deliver files, chapters, manifest and receipts via authorized destination
```

## 6. Regression traps

- **Playlist substitution:** concatenation with tiny silences is not a seamless crossfade mix.
- **Immediate repeats:** distinct filenames for the same musical work are still consecutive repeats.
- **False alternate:** `Blue_Eyes,_Crimson_Jewels(1).mp3` and `(2).mp3` are identical; do not present them as distinct.
- **Unstructured repeat loop:** A→B→C→A→B→C forever technically avoids adjacency, but disregards the request to vary ordering.
- **Wrong total:** full source durations are not the final duration; account for every overlap.
- **Hard cut at 60:00:** prefer planning the overlap math and ending before resorting to destructive trimming.
- **Incorrect art:** a newly generated or semantically similar image is not the user's supplied cover.
- **Wrong media:** an MP3, PNG, or link to a presumed MP4 is not the requested audiovisual deliverable.
- **Claim inflation:** a source artifact, encoded file, validation command and physical user playback are different states.
- **Lost provenance:** keep the original recordings, exact ordered manifest, hashes, transition decisions and technical outputs.

## 7. Acceptance checklist for future OST commissions

- [ ] User-approved source tracks and artwork preserved exactly.
- [ ] Source count, unique-recording count, durations and SHA-256 recorded.
- [ ] All adjacent composition titles differ; genuine takes rotate across nonidentical placements.
- [ ] The pattern varies with repetitions; final movement has intentional musical closure.
- [ ] Transition overlap accounted for in runtime calculation; no deliberate silence at joins.
- [ ] Output duration is within the owner's tolerance (default ±0.25 second if unspecified).
- [ ] Audio format, stereo, measured loudness/peaks and final SHA verified.
- [ ] All junctions auditioned or listening QA plainly marked unverified.
- [ ] Every chapter timestamp validated against actual segment timing.
- [ ] If requested, MP4 contains exact chosen 16:9 cover art and full audio.
- [ ] Final actual file linked; durable Home Center evidence read back.

**Standing principle:** Build **one cohesive listening experience from multiple real recordings**, let repetition serve the atmosphere without becoming conspicuous, and never trade away the commissioned music, visual, runtime or delivery lane for a convenient approximation.
