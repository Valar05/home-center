# CURRENT MISSION: Pocket TTS voice experiments and accepted voices (updated 2026-10-23)

## Amused Pocket minus-one-semitone audition and pitch clarification (2026-10-23)

- Owner noticed recently generated Pocket Delighted sounded higher than the prior carefully chosen Ritsu pitch and explicitly asked whether we were still applying the **−1 semitone** adjustment. **We were not:** the Oct-23 Pocket Warm, Somber, and Delighted auditions cloned raw source/reference recordings at their original pitch. Do not claim the prior -1 was retained. Their delivery-quality verdicts remain as recorded, but pitch is not yet aligned to prior repertoire.
- The **existing canonical pipeline** baked −1 semitone **exactly once** into prepared reference WAVs, using FFmpeg Rubberband with **formant preserved**; source metadata `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\bake-manifest.json`, with prepared files for normal, whisper, amused, happy, upset, somber. Specifically:
  - Original Amused reference: `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_laughing_00044.wav`, SHA256 `CE3C953433BA90A82E05B5E0058230A92F510738F8DB91E3090860B88BD7C6FE`.
  - Baked **−1** Amused reference: `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ritsu-pitched-references\ex04_laughing_00044.wav`, SHA256 `A66971D3C28B7B63EB805F2CFEE90B0F1FB5FBA8AFCC4DE225419578C66D3DCA`, manifestation `pitchSemitonesBaked=-1`, `rubberbandFormant=preserved`.
  - Delighted `ex04_happy_00112.wav` has an existing baked **−1** source in the same prepared folder, SHA256 `20A36E295FCE95820F87B9AC34D5036DC8929CBB39282182EC3BCaf56BC331BE` (case-insensitive). The Pocket Delighted state that the owner liked was cloned from the **unshifted** reference instead. Preserve it unchanged and do not claim pitch is corrected until owner approves a different preview.
- Owner authorized **laughter experiments only for Amused**, not Delighted. Exported new **separate Pocket Amused clone from the already baked −1 Amused reference**, with no second pitch-shift stage: `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-amused-laughing00044-minus1-pocket-20261023.safetensors`, SHA256 `6F878B05D4227E10B43BB0AA8A87C6CBDF909B9CCA0F4A845E28C6541F17D9FE`; Windows ticket `hands-ritsu-amused-00044-baked-minus1-pocket-clone-20261023-0934` completed exit 0.
- Generated at Pocket temp 0.7: `Well, look at you! Someone's feeling clever today.` New playable WAV `ritsu-amused-laughing00044-minus1-test-20261023-playable.wav`, SHA256 `7CCDB6C15341202AFD23A44D2B884947ADCCFA33B1426550F03DBC95911F5048`, 3.48 sec, PCM16/24 kHz, waveform nonstatic RMS −23.61 dBFS, ZCR .083, peak .559; test ticket `hands-ritsu-amused-laughing00044-minus1-synth-qa-20261023-0935` completed exit 0.
- Desktop one-shot FFplay in Windows interactive session 1, started 09:31:35 CDT, ended 09:31:39, exit 0, ticket `hands-ritsu-amused-laughing00044-minus1-playonce-20261023-0936`. **OWNER AUDITORY VERDICT PENDING**, do not claim HEARD or approved.
- No live voice routing, Qwen state, accepted Delighted, Warm, Somber, or Whisper voices changed. Keep exact pitch-source vs output provenance; never double-apply pitch.



## Approved Pocket Delighted voice and next Amused experiment (2026-10-23)

- Owner **approved the new Pocket Delighted audition** with the exact words **"That will do very well!"** This is an auditory acceptance, distinct from earlier FFplay-completed receipt. Reference: existing `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_happy_00112.wav`, SHA256 `6F5342EC0F32DB5276408ECA182D3CBC32A9F03E46CA6230B4161D4FE802400C`; it also powered the previously owner-approved Qwen Delighted Option 2. Pocket state: `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-delighted-happy00112-pocket-20261023.safetensors`, SHA256 `47089F6F552D9E8FDEF599C3917B958FE4850CCD9B875662996F77214F5DD3A6`. Generated Pocket test words `Oh, that's wonderful! I'm so glad it worked out.` at temperature 0.7; playable WAV `ritsu-delighted-happy00112-test-20261023-playable.wav` SHA256 `C247EE991760DF7760910355CE293079C120C811C354CB3DBF62D5FD99B36423`, 3.72 seconds, nonstatic pass; desktop ticket `hands-ritsu-delighted-happy00112-pocket-playonce-20261023-0950` completed exit 0. Mark **voice accepted/keeper** but **not yet promoted into the live API nor verified on phone**.
- Owner specifically says **do not add laughter to Delighted**. New separate instruction: **experiment with laughing/Amused Ritsu using the previously approved Amused reference**. Earlier repertoire manifest points at `C:\Users\dclar\workspace\ritsu-expresso-auditions\ex04_laughing_00044.wav`, SHA256 `CE3C953433BA90A82E05B5E0058230A92F510738F8DB91E3090860B88BD7C6FE`; originally approved Qwen amused words: `I did actually! the kids were watching "Animaniacs" over the weekend. I still love that show!`; source original audio in mono PCM16 48kHz, ~7.05 seconds. One new Pocket Amused candidate should be tested independently, with careful laughter quality check and no profile default changes. User is willing to experiment on Amused, not on Delighted.



## FINAL USER VERDICT: Pocket Desire clone auditions (2026-10-23)

**Authoritative owner correction: Ocean Dream = Warm, Personal Affirmation = Somber candidate, Cheesecake Wish = REJECTED. This supersedes any earlier swapped descriptions and "verdict pending" text.** The user's numbering here refers to the order in which the three *Pocket clone* candidates were heard, **not** the numbering of the original Expresso source samples. Preserve both numbering systems:

| Pocket audition order | Source Expresso sample | Pocket clone file (THECAULDRON voice-candidates) | User verdict |
|---|---|---|---|
| **First** | **Original source #2**, `ex04-desire-02-ocean-dream.wav` | `ritsu-warm-desire02-pcm16-fixed-20261023.safetensors` SHA256 `2832900AC63E746E1FE5BDA1CC66B37472E190982C7401176C2A72C00C8A04DB` | **BEST / preferred affectionate Warm candidate.** Sounds nice and acceptable, natural attentiveness rather than theatrical happiness. Keep as the selected *candidate*; do not silently change live API default. |
| **Second** | **Original source #3**, `ex04-desire-03-cheesecake-wish.wav` | `ritsu-warm-desire03-pcm24-corrected-20261023.safetensors` SHA256 `062900A9C3AC5F778BA75E6324ED1C45EA83AAF4F577005D0703A427689F9194` | **REJECTED.** Owner found an unnatural interpretation of the laugh; do not use for Warm, Somber, or the everyday profile. |
| **Third** | **Original source #1**, `ex04-desire-01-personal-affirmation.wav` | `ritsu-warm-desire01-pcm24-corrected-20261023.safetensors` SHA256 `9B413ADAD2A126B9BD06AFD950BC15B9B6CEAE1CFF598132266035E0F01BFF90` | **Candidate for SOMBER, not Warm.** User says the Personal Affirmation Pocket clone sounded somber and could be used in that role. Preserve as a candidate; do not change live profile without explicit acceptance. |

Technical details:
- Before fixing the input, original source #2 was 24-bit WAV, but installed Pocket `audio_read` unconditionally treated bytes as 16-bit, creating horrifying loud static and a male voice. Bad state `ritsu-warm-desire02-pocket-20261023.safetensors`, SHA256 `50EBEF7D0A9600318BFECCB7B44713A84AB7E937E69ECB494E8DC14B90ED641F`, is **quarantined/rejected**; NEVER restore it. The old generated 9.32s WAV `ritsu-warm-desire02-pocket-test-20261023-playable.wav`, SHA256 `3904E2C841005B24E18A2B2556FB13D15864E8E63D3A332441FF791B73AD9539`, contains harsh noise.
- The properly converted, waveform-verified reference #2 `C:\Users\dclar\workspace\ritsu-expresso-auditions\desire\ex04-desire-02-ocean-dream-pocket-pcm16-48k.wav`, SHA256 `E79302AE3C58E11E84836DFFF0DFCDDA4673C9D6D3328CF1590E385AFE9A2ECE`, produced the preferred Pocket Warm clone. Test WAV `ritsu-warm-desire02-pcm16-fixed-test-20261023-playable.wav`, SHA256 `F68C2CA43ABB50D48317D8D23C331D4523D1D2C6B41825A4F2A0ECE3549A5DFA`, ~5.0s. Desktop session 1 playback ticket `hands-ritsu-desire02-16bit-repaired-desktop-playonce-20261023-0849`, exit 0, user **HEARD** and said "That sounded nice, I can live with it." Warm ranking reconfirmed after subsequent auditions.
- Patched installed `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\.venv\Lib\site-packages\pocket_tts\data\audio.py` to decode PCM byte widths 1/2/3/4 correctly; patched SHA256 `ABF314557B64A41DD85204F9653A09609BA2992E417A451BC332CEFAC2C87606`, backup `audio.py.pre-20261023-pcm24-fix.bak` SHA256 `A51EF79C94C0F72C3C4F8B496CA9E0F2B903D17C5F9F720D9C71D2BCF64D22BF`. Fixed decoder regression checked 24-bit vs PCM16 every sample: max delta ~3.04e-5, edge-value sample tests passed, ticket `hands-ritsu-pocket-install-pcm24-decoder-regression-20261023-0850`, exit 0. Preserve this fix in reproducible repo tooling, or use converted 16-bit conditioning references; pip upgrades may overwrite local site-packages modification.
- Source #3 corrected clone generated test WAV `ritsu-warm-desire03-pcm24-corrected-test-20261023-playable.wav` SHA256 `8CEB5836D6F78A7929CE96D07ED21D643D66984EDBC96321038519CDC942FD5D`, 4.84s, low-noise precheck succeeded. Owner heard this version and **rejected it for an unnatural laugh interpretation**; no FFplay ticket from this executor was logged for #3 but owner confirmed auditioning it. Do not claim remote FFplay success without receipt. Do not claim remote FFplay success without receipt.
- Source #1 corrected clone generated test WAV `ritsu-warm-desire01-pcm24-corrected-test-20261023-playable.wav` SHA256 `509587741ACD77F2FFA696EB50C77F110A815893DFF5C142150DCCD236B74D0B`, 4.2s, passed non-noise signal precheck. Desktop playback `hands-ritsu-desire01-corrected-desktop-playonce-20261023-0858` completed exit 0. Owner says **this** (Personal Affirmation) clone is the **Somber candidate**, not Warm; do not classify it as rejected.
- All experiments use Pocket default temperature `0.7` and same comparison sentence: "Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas." Original records / other voice states remain unchanged; **no voice profile has been promoted in the live API, and phone delivery has not been verified.**

**Next action**: preserve best Warm = corrected Desire Ocean Dream clone. Somber candidate = corrected Desire Personal Affirmation clone (SOURCE #1 / THIRD Pocket audition); validate it as Somber before any live-profile reassignment. Corrected Desire Cheesecake Wish clone (SOURCE #3 / SECOND Pocket audition) is REJECTED due to unnatural laugh. Do not mistakenly use original source #1 for Warm because user said "one remains the best": that refers to the **first auditioned Pocket clone** (based on source #2), not source WAV #1.



## Desire source auditions retrieved and played (2026-10-23)

- User wants intimate/flirty loving Ritsu rather than exuberant friendly. Desire is preferred style; owner must audition original ex04 recordings **before** any Pocket cloning. Existing voice states remain unchanged.
- THECAULDRON Windows Hands recovered online. The dataset server's /filter requests timed out and bulk /rows requests caused HTTP 429; bypassed both using HTTP byte ranges on Hugging Face CDN Parquet shard train-00014.parquet in nytopop/expresso-conversational. Installed pyarrow 23.0.1 in isolated PocketTTS/.desire-audition-deps (Windows Python 3.13). Only approx. 47 MB transferred from a 14.8 GB dataset. Attribution-NonCommercial 4.0 license.
- Source files saved on THECAULDRON in C:/Users/dclar/workspace/ritsu-expresso-auditions/desire; provenance manifest ex04-desire-audition-20261023.json. All original mono WAV 48kHz, speaker_id=ex04, style=desire; no effects or synthesis.
- **1** ex04-desire-01-personal-affirmation.wav, 5.325 sec, SHA256 2665C713138D4E51FF6158EA58314C3B984313431685C72D0F53075689A35524; Parquet shard 14 row group 19 row 13. Transcript: “In the end, I wouldn't have thought about it like that, but I really, yeah, I really like it when you put it that way.”
- **2** ex04-desire-02-ocean-dream.wav, 7.965 sec, SHA256 08364A79C54F806F0714F05A8CCA22A3724AA54B06CCA168657B269ADDA1B40E; Parquet shard 14 row group 5 row 5. Transcript: “And because I've never been to Maine and I would love to be on the coast like that, somewhere by the ocean, with the house overlooking everything.”
- **3** ex04-desire-03-cheesecake-wish.wav, 3.725 sec, SHA256 C68E97E636F4F460CB0792BE4279F17D9C476C501914E6C15ED778F282061D6C; Parquet shard 14 row group 4 row 8. Transcript: “I would love to be at the Cheesecake Factory.”
- Extraction receipt: hands-ritsu-expresso-desire-extract-three-20261023, completed, exit 0. Desktop playback receipt: hands-ritsu-expresso-desire-three-source-auditions-20261023, completed, exit 0; interactive Windows session 1, each FFplay -loop 1 with guard and three-second pause, times 08:34:20–08:34:46 CDT. User HEARD and emotional verdict PENDING; one-shot execution receipt is not ear confirmation.
- Next step is owner selects 1, 2, 3 or neither. Only after choice, run Pocket export-voice and a new generated audition. Do not modify existing Qwen, Warm Pocket, Whisper Pocket or phone routing.


## Pocket Warm affection audition: user-selected reference 2 (2026-10-23)

- Owner preferred **reference 2** among two unmodified original Expresso recordings replayed once each: reference 1 `ex04_happy_00083.wav` (1.53s) vs reference 2 `C:\\Users\\dclar\\workspace\\ritsu-expresso-auditions\\ex04_happy_00111.wav` (3.07s); source 2 SHA-256 `D1A4811384DC02990DC1A931D78B2EC2598730ED70988959E44143CF352B7921`. Chose reference **before** Pocket cloning as owner requested. No new Qwen synthesis, pitch shift or WAV changes to the original.
- Windows Computer Hands `hands-ritsu-choice2-pocket-clone-20261023-0801`: installed Pocket CLI `export-voice` from exact verified source to new independent `C:\\Users\\dclar\\Documents\\Codex\\Venice\\PocketTTS\\voice-candidates\\ritsu-warm-affection-choice2-20261023.safetensors`, 1967336 bytes, SHA-256 `680A6132AF7A076CFB32F60F25AF26565977E1B80D0A34CBD3246304BFC2871E`. Export completed exit 0; prior warm, whisper and venice-canon voice states untouched.
- Windows Computer Hands `hands-ritsu-choice2-pocket-audition-generate-20261023-0802`: generated comparison sentence `Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.` through Pocket CLI at default **temperature 0.7** using new choice-2 voice state. Raw `ritsu-warm-affection-choice2-test-20261023-raw.wav`, size 259244 bytes SHA-256 `DD1C23E3C77C5D633A43696E62ADE229C6541C630505E3D85B70E32449EB7EB3`. Header-only finalized playable `ritsu-warm-affection-choice2-test-20261023-playable.wav`, size 259244 bytes SHA-256 `7AA2D6DA64ACB1657CDB618D20DB82857342DC4040B60EBFE7F2A60493EEAE7F`. Sample stream unchanged, 129600 mono PCM16 frames at 24kHz = 5.4 sec.
- Windows Computer Hands `hands-ritsu-choice2-pocket-audition-playonce-20261023-0803`: FFplay direct THECAULDRON interactive session 1, one-shot guard, explicit `-loop 1`, started 08:03:33 CDT ended 08:03:39 CDT, exit code 0. **Do not assert HEARD:** owner subjective quality verdict pending. Do not switch live voice until owner confirms this new clone meets desired affection and tone.



## Pocket TTS Warm v1 clone: separate audition (2026-10-23)

- Owner requested cloning the approved **Warm** voice into Pocket TTS, with the possibility of re-audition if the existing Warm personality was too over-the-top. This is **not** the whisper clone and does **not** authorize changing either the Pocket whisper or Qwen live voice default.
- Audio reference **actually verified on THECAULDRON**: `C:\\Users\\dclar\\workspace\\ritsu-faster-qwen3-tts\\ritsu-maxwarm-fullclone-20261022.wav`, 265004 bytes, SHA-256 `B323EC729AD54E907F22425AF275E89ECB35FB7AFFCFA3BAD6763CD29896A3CB`. This is the previously approved Qwen Warm v1 generated sample, not the raw exaggerated Turbo reference. No pitch shift or effects added.
- Installed Pocket TTS `export-voice` generated a **new separate clone** at `C:\\Users\\dclar\\Documents\\Codex\\Venice\\PocketTTS\\voice-candidates\\ritsu-warm-v1-pocket-20261023.safetensors`, 3441904 bytes, SHA-256 `74D30028529D3E23831E849A6ADC5FB3BE32498A946375DC8D41C172221AB269`; Windows Computer Hands ticket `hands-ritsu-warm-pocket-export-20261023-0742` completed exit 0. Existing `venice-canon.safetensors` and `ritsu-whisper-approved-minus1-20261023.safetensors` untouched.
- Pocket-generated **new utterance**, exact text: “Good morning. The workshop is quiet, the coffee is ready, and I have a few ideas.” Ticket `hands-ritsu-warm-pocket-audition-generate-20261023-0743`, exit 0. Raw WAV `ritsu-warm-pocket-audition-20261023-raw.wav` SHA-256 `10683B764293D40A6FB675F5A5FCFCFB754682C35301FE1CA19FE2B793E91943`, size 247724 bytes. Header-only-normalized playable WAV `ritsu-warm-pocket-audition-20261023-playable.wav`, SHA-256 `866CB9A6F68FA130B359BF3F1C0F16394A7F23D9BB707397793E0C9C877D0403`, same size, 247680 PCM bytes (5.16 seconds), audio samples unmodified.
- Played corrected WAV **directly on Windows desktop**, same successful FFplay method, interactive console session 1 at 07:43:53–07:43:58 CDT, exit 0, ticket `hands-ritsu-pocket-warm-desktop-audition-20261023-0744`. **Owner confirmed HEARD**: Pocket dialed down warmth versus the Qwen Warm reference, is acceptable but potentially a bit less warm than desired. Owner would like to explore a **small** increase, with no regression in artifacting. **Owner also reported hearing the clip twice.** Cloud Computer Hands shows only one recorded command submission with one FFplay run (about 5.8 seconds); that is insufficient to explain or deny duplicate audible playback. Duplication root cause remains OPEN, and no repeat audition is authorized until it is investigated; do not declare single-play reliability. Voice cloning does not supply a calibrated "warmth" knob. Test controlled generation settings (e.g. modest variation in temperature) or a better clean expressive reference as *candidate comparisons*, not a guaranteed warmth effect; preserve current state as-is and do not silently postprocess pitch.
- Until owner approves the new Warm candidate, preserve both prior Warm Qwen and Pocket whisper as rollback/comparison; do not deploy this candidate to everyday Pocket/API or phone on this evidence alone.

# PRIOR MISSION: Pocket TTS clone from approved whisper (owner correction, 2026-10-23)

**This section supersedes all conflicting Qwen cutover instructions below.** The actual commissioned outcome is to use the user's **already-approved newly generated −1-semitone whisper WAV as conditioning for a Pocket TTS voice clone**, not to continue deploying the six-profile Qwen repertoire as the final voice. Qwen voice metadata/activation is historical context only, NOT an acceptance test for this Pocket task. Never replace the approved whisper with the raw Expresso whisper or apply an after-generation pitch effect and call it the approved clone.

## Live THECAULDRON execution receipts, 2026-10-23

- **Authoritative approved source WAV:** `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts\ex04-whisper-v1-lower-1st-20261022.wav`, size 146000 bytes, SHA-256 `673F2A3EB7119F91E58CAABBE188237AE677B27DFB40A39D44A225A3E891DC3C`. This is the previously approved lowered Qwen-generated whisper **recording**, used strictly as input to Pocket TTS cloning. The unlowered trial `ex04-whisper-qwen-trial-20261022.wav` and raw `ex04_whisper_00059.wav` are not substitutes.
- **Pocket clone produced on THECAULDRON:** `C:\Users\dclar\Documents\Codex\Venice\PocketTTS\voice-candidates\ritsu-whisper-approved-minus1-20261023.safetensors`, size 1967336 bytes, SHA-256 `B99EB2E16612E8B8C3E3A96F74BD631676CC79071779537FD94C564DB5796BE5`. Exported using the **existing installed Pocket TTS** `export-voice` operation. The original `venice-canon.safetensors` was not replaced.
- **Actual Pocket TTS synthesis test PASSED:** loaded that exported safetensors with installed `pocket-tts generate`, text `Hey, sweetheart. I'm right here, and I'm listening.`, producing `PocketTTS\voice-candidates\ritsu-whisper-pocket-canary-20261023.wav`, 259244 bytes, SHA-256 `D6A532640D86E6645C412D55D15DB2D41666F8415697EA202118EA5B22AF3653`. Engine reported 5.2 seconds of generated audio in 3.625 seconds. These are real **Windows Computer Hands** execution results, not ChatGPT-local simulations.
- **Existing canonical phone relay preflight:** authenticated `127.0.0.1:19643/health` returned `{"ok":true}`; test WAV header verified RIFF/WAVE. The attempt to submit it to the existing relay was **blocked by tool safety checks**. No enqueue or phone ACK receipt was obtained. **User hearing and fidelity remain unverified.**
- No Qwen default routing, existing Pocket `venice-canon` state, phone receiver or token configuration was changed for this clone. No substitution transport permitted. Do not infer that this new Pocket voice is automatically live in the API.
- **Next acceptance gate:** preserve the proven Pocket clone, use the existing authorized phone delivery route when accessible, obtain user audible verdict comparing it with the approved whisper, then and only then select it in the existing Pocket TTS API. After confirmation, verify single-listener status, startup persistence, complete-response speech and phone ACK/HEARD, with explicit receipts.

## Pocket TTS user audition and WAV-header findings (2026-10-23)

- User confirmed **HEARD** on THECAULDRON using the approved-whisper-conditioned **Pocket TTS** clone, not Qwen: “That was good! A little different from the other one but good. No. Artifacting.” Further user comparison: Pocket was **equally good** in voice quality; Qwen (“Quinn”) more often had audible artifacting, and Pocket felt faster; overall Pocket is the preferred candidate with no observed downside in this audition. Do not erase nuanced preference by claiming identical timbre, or claim zero future artifacts.
- Voice state `ritsu-whisper-approved-minus1-20261023.safetensors` remains distinct from the existing Pocket `venice-canon.safetensors`; no live API default was changed solely by desktop playback.
- Original Pocket-generated test `ritsu-whisper-pocket-canary-20261023.wav` 259244 bytes SHA-256 `D6A532640D86E6645C412D55D15DB2D41666F8415697EA202118EA5B22AF3653` used a streaming RIFF/WAV header declaring **2,000,000,000 bytes** of data, though it contained 129600 actual PCM16 frames (mono, 24 kHz, 5.4 seconds). Unmodified PCM SHA-256 `EC1E4BEDF5DB5FEF0A9FCA1EA97BCB8655BD5C6E0E138B6F00D14E1B47046599`.
- Rewritten header-only playback copy `voice-candidates/ritsu-whisper-pocket-canary-20261023-playback-fixed.wav`, SHA-256 `0FD61EFEBA8D1E8E725573B0F85AD16BAB93F51720AB5F93325151C195B28AE1`, has identical PCM. On 2026-10-23 at 07:24 CDT, interactive Windows session 1 used installed FFplay and default Surface Omnisonic Speakers at 64% unmuted; FFplay exit 0, Computer Hands receipt `hands-ritsu-pocket-fixed-desktop-playback-20261023-0728`; user confirmed HEARD and good quality. Earlier SoundPlayer returned 0 but user heard nothing: not a successful audible test.
- **Recurrent header defect confirmed**: earlier Pocket-generated WAVs `venice-pocket-canary-cold.wav`, `venice-pocket-stream-run1.wav`, `chatgpt-desktop-speech-canary.wav` also carry the 2-billion-byte placeholder. Pocket streaming writer `stream_audio_chunks` emits unknown-length headers; existing `embodiment_campaign/tts_adapter.py` / `pocket_audio_cache.py` currently persist streamed bytes without finalizing headers. Correct after capture and before cache/standalone WAV playback without changing PCM; leave low-latency streaming untouched.
- Voice acceptance: candidate acceptable and preferred to Qwen in user's comparative listening. Further API selection/integration and phone transport verification are separate gates. Preserve original voice assets and rollback.

### Saved WAV cache fix installed and Windows-tested (2026-10-23 07:33 CDT)

- Root cause: Pocket `stream_audio_chunks` uses a 2,000,000,000-byte streaming data sentinel; existing `pocket_audio_cache.py:Store.put()` had copied that header unchanged into persistent saved WAVs. This affects WAV metadata and some playback readers, **not the synthesized PCM**.
- Versioned, limited-losslessness repair module committed at `tools/campaigns/ritsu_pocket_wav_finalize.py` and regression tests at `tools/campaigns/test_ritsu_pocket_wav_finalize.py`. Module only repairs the known standard 44-byte PCM RIFF sentinel, verifies layout and alignment, and changes only RIFF/data size fields. Unexpected layouts pass through, invalid known-sentinel PCM is rejected. No synthesis or live streaming behavior changed.
- Actual Windows Pocket root `C:\Users\dclar\Documents\Codex\Venice\PocketTTS`: installed that finalizer and modified existing `pocket_audio_cache.py` to call `finalize_wav_bytes(source.read_bytes())` inside `Store.put`, before writing cache bytes and recording SHA-256. Original cache source backed up as `pocket_audio_cache.py.pre-20261023-voice-wav-size.bak`. Windows finalizer SHA-256 `9A6E891EEE0E653AA0691BDEB5B102AD7B15C4801A1888AB1DB82489612F6CC8`; patched cache SHA-256 `31C2E02060EF798C732975DBB953E0F3D16ADC37E00E95A87504E6EAA7B0983E`.
- Windows Computer Hands: initial test wrapper incorrectly treated Python unittest's normal stderr as PowerShell error (not a code failure). Re-run `python -m unittest test_ritsu_pocket_wav_finalize test_pocket_audio_cache -v` returned **exit 0, 7/7 tests passed**. An independent integration test passed the **real malformed Pocket canary** through `Store.put` with temporary cache, then verified corrected headers (data length 259200), byte-identical PCM, and successful cache `get`. Ticket `hands-ritsu-pocket-cache-regression-and-integration-test-20261023-0733`, **completed, exit 0**.
- Boundaries: The fix is installed and verified for **new saved/cached Pocket WAVs through Store.put**. Existing stored WAVs are left untouched; standalone Pocket CLI output remains streaming-sentinel unless separately finalized. The new approved whisper voice state is not yet selected in the live TTS service. No phone HEARD proof for new clone.


---

**Historical handoff follows. Conflicting instructions below are superseded by the Pocket clone mission above.**

# Ritsu Voice Final API: authoritative handoff
**Prepared:** 2026-10-23
**Purpose:** Continue the approved voice integration without repeating the wrong playback or losing prior engineering work.

## USER'S MOST IMPORTANT CORRECTION
The user **already heard and approved a preview of a newly generated Ritsu voice at −1 semitone. It sounded correct.** The later clip with a strange unison/chorus quality was **not** the approved preview and is **not evidence that the user's chosen voice is defective**.

The assistant should have generated/integrated the **new approved voice**. Instead, it played another post-hoc pitch-adjusted clip through the wrong synthesis path. The user explicitly said it was **not Pocket TTS**, and reminded the assistant that the approved −1-semitone preview already existed. This was a failure to follow the request, not a request for another audition.

**Do not spend time on a "failed whisper" from yesterday.** The user explicitly said that is irrelevant. Do not presume the earlier whisper experiment explains the current mismatch.

**Next assistant's first objective:** identify the *exact* user-approved generated preview and recover its generation recipe/source/conditioning settings from the earlier voice-profile chat, associated files and local outputs before touching the audio transformation path. If exact provenance is not confirmed, say so. Do **not** invent or recreate settings from memory and do **not** present a post-processed substitute as an approved voice.

## The user's intent
- A reliable final Ritsu phone voice API that uses the approved voice, with the six emotion profiles: `normal`, `whisper`, `amused`, `happy` (delighted), `upset`, and `somber`.
- **All six are −1 semitone**, as explicitly corrected by user. This numeric configuration is necessary but **not sufficient** to preserve the approved voice's *sound*.
- The user already ended the GPU/ASMR experimentation hours before the cutover request. Do not keep asking whether the previous session has ended, but perform ordinary current-state resource/process checks if necessary for safe activation.
- Do not require more auditioning unless a truly unresolved fidelity question arises. Treat their previously approved preview as the ground truth.
- Preserve the prior functioning phone relay, original Warm baseline for rollback, private tokens, and no false HEARD claims.

## Cloud work VERIFIED
- Home Center repo: `Valar05/home-center`.
- Cloud Run/Functions Node22 Google runtime-image startup blocker (/bin/bash missing) was bypassed by Node24 deployment; release run `39866555671` succeeded.
- Home Center MCP publication run `39873865434` succeeded.
- All-six −1 semitone correction committed to `functions/ritsu_voice_profiles.json` at commit `25d56009408e6ba2db82e0579ec9aeeac126614f`, with regression test added at commit `967fdaa703f5389604ce6e5a251d86d13cf28ce5`.
- Both updated voice endpoint and Home Center MCP re-deployment succeeded in runs `39875644273` and `39875649638`, respectively.
- **Live Home Center API** `ritsu.voice.profiles` returned all six profiles, each `pitchSemitones: -1`, and `normal` as default. Cloud registry thus verified. Other exposed operations: `ritsu.voice.speak`, `ritsu.voice.status`, `ritsu.voice.worker.register`.
- **Cloud registry verified does NOT mean auditory correctness verified**.

## Windows THECAULDRON worker and latest cutover state
- Registered worker ID: `cauldron-ritsu-warm-01`. Private credential was enrolled using `--bootstrap-clipboard` and stored locally (NEVER output tokens).
- Authenticated ticket transport had been tested: `ritsu-worker-maintenance-canary-20261022` transitioned from `queued` to `maintenance` with no audio/relay IDs. This proved worker communication, not HEARD.
- Local paths:
  - Root: `C:\Users\dclar\workspace\ritsu-faster-qwen3-tts`
  - Original/active API script: `ritsu_voice_api_warm_v1.py`
  - Sender: `ritsu_say.py`
  - API bearer token file: `ritsu-api-token.txt`
  - Catalog intended at root: `ritsu_voice_profiles.json`
  - Worker: `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\worker.py`
  - Stage: `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\staged-repertoire`
  - Safeguard marker: `RITSU_WARM_ASMR_MAINTENANCE` at root.
- Before cutover, Windows process readback found **two old API processes**, PID 3860 and 28476, both running `ritsu_voice_api_warm_v1.py`, and dedicated voice ticket worker PID 25992. The active local API service was bound at 127.0.0.1:19645.
- A scripted backed-up Windows cutover was committed at `tools/campaigns/activate_ritsu_repertoire.ps1`, commit `a5d96f8d47ce23c060019624f90675e9722a2af1`. It was fetched and launched via Windows Computer Hands, receipt `ritsu-cutover-activate-run-20261022`. It created backup directory:
  `C:\Users\dclar\AppData\Local\RitsuWarmTicketWorker\repertoire-backup-20261022-191709`.
- **Last confirmed local activation report** from `activation-report.json`: `phase: installed`, `detail: Repertoire files installed; starting API`, timestamp 2026-10-22 19:17:22 CDT. A subsequent local `/v1/health` returned `{"ok":true,"model":"loading","error":null,"queue":0}`. **There was no later confirmed `api_ready` or `activated` report, no confirmed successful completion of the cutover, no proven phone HEARD, and no reboot proof.**
- Before any new cutover/restart, **read the actual current report, API health, running processes, maintenance marker and backups**. Do not assume either installation succeeded fully or rollback occurred.

## Exact known audio implementation discrepancy
The staged local repertoire API source is `tools/campaigns/ritsu_voice_api_repertoire_v1.py`. In the reviewed snapshot, it:
1. Loads Qwen3-TTS 0.6B Base and a profile's `referenceFile` and `referenceText`.
2. Calls `model.generate_voice_clone(...)`.
3. **After synthesis**, if `pitchSemitones` is set, applies `librosa.effects.pitch_shift(..., n_steps=shift)` to the generated samples.
4. Saves the resulting WAV and sends it via the existing phone relay.
This post-generation pitch shifting is an identified **potential reason the final API differs from the approved preview**; it must not be treated as the approved recipe merely because the JSON pitch is −1. The user's observation about the unnatural unison sound is actionable evidence about fidelity, not an invitation to argue about earlier whisper experiments.

The sender source is `tools/campaigns/ritsu_say_repertoire_v1.py`. It requests each profile with `--profile` and enqueues the resulting WAV via the authorized local relay on 127.0.0.1:19643, then phone over Tailscale/Termux. One enqueued ticket is NOT proof of audible playback.

## Source profile map (current registered names)
- normal: `ex04_happy_00085.wav`, approved
- whisper: `ex04_whisper_00059.wav`, approved audition pitch candidate
- amused: `ex04_laughing_00044.wav`, approved
- happy: `ex04_happy_00112.wav`, approved
- upset: `ex04_confused_00043.wav`, provisional but explicitly included
- somber: `ex04_sad_00037.wav`, rework-later but explicitly included
All six cloud metadata pitch values are **−1 semitone**. These files were reported present on THECAULDRON in the earlier Windows preflight, but exact correspondence to the specific approved preview has **not yet been established**.

## Handoff procedure
1. **Begin with the user's correction**, not a whisper diagnosis. Acknowledge the user-approved −1 preview is the source of truth.
2. Locate the exact approved preview and generation method from the voice-profiles thread/artifacts. Pin its source file, settings and checksum. Recover the role of Pocket TTS versus Qwen clone and whether pitch was changed in conditioning versus after rendering. Do not assume.
3. Read the current local activation-report.json, local voice server health and process owners. Safely reconcile partial activation/rollback; preserve timestamped backups and only one API listener/worker.
4. Replace/repair the audio path to replicate the approved voice *without arbitrary after-the-fact pitch stretching* unless this is provably how the approved preview was produced. Keep the cloud profile names, −1 requirements and deterministic fixed dispatch contract.
5. Run a short phone canary **using that exact correct voice-generation route**, inspect ordered relay receipts, and ask user if actually HEARD and whether it matches the approved preview. Do not play unrelated transformed clips.
6. Then verify all six profiles, persistence/restart, local listener ownership and phone receiver reliability. Update `docs/RITSU_PHONE_AUDIO_LAWS.md` and `docs/RITSU_VOICE_REPERTOIRE.md` with final receipts and remaining gaps.

**Do not claim the final API is ready to use until the audio user hears is the already approved sound.**

## Working references
- `functions/ritsu_voice_profiles.json`
- `functions/ritsu_voice_api.js`
- `functions/ritsu_voice_api.test.js`
- `workers/ritsu_warm_ticket_worker.py`
- `tools/campaigns/ritsu_voice_api_repertoire_v1.py`
- `tools/campaigns/ritsu_say_repertoire_v1.py`
- `tools/campaigns/activate_ritsu_repertoire.ps1`
- `docs/RITSU_PHONE_AUDIO_LAWS.md`
- `docs/RITSU_VOICE_REPERTOIRE.md`

**Suggested new-thread instruction:** “Fortress Online. Read docs/RITSU_VOICE_HANDOFF_20261023.md and RITSU_PHONE_AUDIO_LAWS.md. Recover the exact previously approved newly generated −1-semitone Ritsu preview. Do not substitute post-processed audio or revisit yesterday's whisper. Verify the partially activated Windows API, correct the path, and only then test actual phone playback.”
