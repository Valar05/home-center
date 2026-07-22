# Drive Narrate Automatic Voice Planning

Drive Narrate has one user-facing render path. Opening and rendering a Google Doc automatically builds a voice plan from the Home Drive Character Voice Orientation Registry, then generation follows that plan for each chunk. There is no separate Split Voice render button or command.

## Owner

What existing tool or system should own this capability?

The existing Home Center Drive/Docs reader owns source document intake and render orchestration, `app/src/main/assets/home_drive_character_voice_registry.md` owns speaker-to-voice orientation, and `GoogleDocAudioLibrary` owns saved section audio manifests. The Drive workspace stores plan/render artifacts around those systems; it is not a separate user flow.

## Render Contract

- Every `RENDER`, `RERENDER`, autoplay first chunk, and playback-triggered section generation uses the registry voice-plan speech profile.
- `CHARACTER:` labels, aliases, `[voice:*]`, and `[speaker:*]` create speaker boundaries.
- Each section stores the resolved `SectionVoiceAssignment` before generation and reuses that assignment for provider voice selection.
- Old role-default or single-voice cache entries are incompatible with the registry voice-plan profile and cannot restore into the new render.
- The Drive narration profile remains authoritative for provider, model, narrator, dialogue default, notes default, and registry fingerprint.
- Unknown voices are marked in the plan; Home Center does not perform voice interpolation as a separate product.

## Drive Workspace

Root folder:

```text
Home Center Voice Split Rendering
```

Subfolders:

```text
01 Intake Documents
02 Split Plans
03 Rendered Chunks
04 Final Mixes
05 Voice Registry Snapshots
99 Failed Runs
```

The workspace preserves generated plans, chunks, final mixes, registry snapshots, and failed runs. The app surface still exposes one render path.
