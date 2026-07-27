# SFX Forge contract

SFX Forge is the first-class Home Center surface for turning immutable physical recordings into mechanically verified SFX evidence, conservative descendants, and deterministic source-conditioned candidates.

Registry version: `2026-07-27.sfx-forge-v3`

Engine version: `home-center-sfx-forge-v1.1`

Schema version: `home-center.sfx-forge.v1`

## Boundaries

- `audio.ingest_drive` owns immutable intake and provenance. Forge never creates or replaces the canonical source.
- `sfx.analyze_source` owns verified decode, standards-based measurement, transient candidates, waveform/spectrogram evidence, and a hashed PCM working descendant. It is provider-free.
- `sfx.transcribe_slate` owns a hashed 16 kHz mono FLAC descendant and timestamped Google Cloud Speech-to-Text evidence through project identity.
- `sfx.segment` owns ordered event-manifest validation, raw cuts, conservative cleaned dry cuts, rejected cuts, component categories, and review reels.
- `sfx.render` owns deterministic source-conditioned candidate construction from named physical regions and semantic controls.
- `sfx.status` attaches to existing work. It never silently repeats paid transcription.
- `sfx.artifacts` verifies durable descendants by byte count, SHA-256, header, and optional decode.
- `audio.render` remains a downstream scene assembler. Its RMS-derived `integratedLufs` field is not Forge loudness evidence.
- The legacy oscillator-based `sword_impact` preset is not an SFX Forge source, recipe, candidate, or catalog authority.
- Execution authorization (`approved: true`) permits the cloud operation to run. It does not mean artistic acceptance.
- Every Forge result remains `humanAcceptance: "unreviewed"` until Drew records a separate review decision.

## `sfx.analyze_source`

Required input:

```json
{
  "sourceRef": "gs://home-center-generated/audio/.../Track-31.m4a",
  "expectedSha256": "64 lowercase hex characters",
  "requestId": "stable-idempotency-key",
  "approved": true,
  "family": "heavy-bag",
  "transcription": {"enabled": false}
}
```

The source must already live under the canonical generated-audio bucket. The exact parent hash is mandatory. The operation:

1. reads and hashes the immutable source;
2. decodes a non-normalized 48 kHz stereo PCM16 working WAV;
3. measures integrated loudness and true peak with FFmpeg `ebur128=peak=true`, explicitly labeled EBU R128 / ITU-R BS.1770 evidence;
4. detects ordered transient candidates without assigning artistic meaning;
5. publishes the working WAV, waveform, spectrogram, and analysis JSON with readback hashes.

Transcription is deliberately separate so a provider failure cannot rerun or contaminate mechanical analysis.

## `sfx.transcribe_slate`

Required input:

```json
{
  "sourceRef": "gs://home-center-generated/audio/.../Track-31.m4a",
  "expectedSha256": "64 lowercase hex characters",
  "requestId": "stable-idempotency-key",
  "approved": true,
  "family": "heavy-bag",
  "transcription": {
    "languageCode": "en-US",
    "model": "latest_long"
  }
}
```

The operation re-verifies the immutable source, creates a non-normalized 16 kHz mono FLAC recognition descendant, uploads it with parent lineage and a deterministic FFmpeg recipe, and submits its GCS URI to Google Cloud Speech-to-Text v1 using Application Default Credentials. It returns ordered segments, word start/end timestamps, per-word confidence when available, provider configuration, and response hash.

The OpenAI API is not used or bound to Home Center MCP. The transcript remains assistance; `semanticAuthority` is still `source_audio`.

## `sfx.segment`

Segmentation requires an ordered event manifest. Unknown information must remain `unknown`; the server does not reconstruct labels from chat memory.

Each event contains:

- `eventId`
- `labelSlateText`
- `spokenLabelTimeRange`
- `impactTimeRange`
- optional `takeNumber`
- `strikeActionClass`
- `eventType`
- `eventDomain` (`impact`, `bag_movement`, `room`, `air`, or `other`)
- position, distance, glove, and force labels
- confidence and ambiguity notes
- `disposition` and optional rejection reason

The operation writes:

- raw event cuts;
- conservative cleaned dry cuts;
- rejected raw cuts;
- room, bag movement, handling, rub, miss/air, and other component categories when named by the manifest;
- an audition reel using the source’s spoken slate before each level-matched cleaned cut;
- a level-matched raw-versus-cleaned A/B reel;
- separate impact-only and bag-rocking audition reels when both domains are present;
- a complete parent-linked manifest and cleanup recipe.

`sourceMechanism.fixtureType` is part of the evidence contract. A floor-standing/freestanding bag rejects suspended-bag event and layer roles such as `suspension`, `chain`, and `chain_rattle`. Its movement vocabulary is `bag_rocking`, `base_flex`, `base_rock`, `return_swing`, and `floor_coupling`. Impact and movement cuts may overlap in source time, but remain separate descendants and review lanes.

Cleanup is intentionally small: 25 Hz high-pass plus click-prevention fades. It performs no denoise, normalization, tail truncation, or canonical rewrite.

## `sfx.render`

Every candidate declares named physical layers and exact source time ranges. Supported semantic controls are normalized values from 0–1:

- `force`
- `mass`
- `distance`
- `intensity`

Every candidate also declares an `outputKind`:

- `impact_only` may use impact layers but not bag-movement layers;
- `bag_movement` may use floor-bag movement layers but not impact layers;
- `composite` is an explicit recombination and is never implied by a long impact tail.

For floor-standing bags, `suspension` and chain roles are invalid rather than aliases for rocking.

The current deterministic transforms are gain, high/low-pass shaping, compression, restrained saturation, panning, timing, and limiting. No pitch-shift variation exists in Forge v1.

When a recipe asks for multiple candidates:

- candidates must not use identical source-region sets;
- the family must use at least two distinct physical source regions;
- every output preserves the full recipe, source lineage, controls, seed, and recipe SHA-256;
- candidate state is `candidate`, never `accepted`.

## Verification

Mechanical acceptance requires:

- exact parent source hash;
- decoded working descendant hash;
- readback equality for every output;
- EBU R128/BS.1770 labeling for loudness and true peak;
- nonempty ordered event manifest before segmentation;
- separated raw, cleaned, and rejected lanes;
- deterministic canonical recipe hash;
- explicit source regions for every layer;
- no source replacement;
- no fabricated human acceptance.

Human listening remains a separate authority.

Integrated loudness is not reported for a sub-400 ms or otherwise ungated impulse. FFmpeg's `-70 LUFS` gate floor is preserved only in parser evidence and normalized to `integratedLufs: null`, `integratedLoudnessApplicable: false` in the candidate receipt. True peak, duration, decode, clipping, signal metrics, and hashes remain valid. Longer movement or ambience candidates may carry applicable integrated loudness.
