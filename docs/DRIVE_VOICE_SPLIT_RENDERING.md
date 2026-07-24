# Drive Narrate Automatic Voice Planning

Drive Narrate has one user-facing render path. Opening and rendering a Google Doc automatically materializes a voice plan from the Home Drive Character Voice Orientation Registry, then generation follows that plan for each chunk. Render and Rerender do not create Google Docs. There is no separate Split Voice render button or command.

## Owner

What existing tool or system should own this capability?

The existing Home Center Drive/Docs reader owns source document intake and render orchestration, `app/src/main/assets/home_drive_character_voice_registry.md` owns speaker-to-voice orientation, and `GoogleDocAudioLibrary` owns saved section audio manifests. Routine renders store the effective plan in the reader/audio manifest path. The Drive workspace is only for explicit saved artifacts; it is not a render side effect.

## Render Contract

- Every `RENDER`, `RERENDER`, autoplay first chunk, and playback-triggered section generation uses the registry voice-plan speech profile.
- `RENDER` and `RERENDER` must not call `docs.create` or create plan/workflow Google Docs.
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

The workspace can preserve explicitly requested artifacts. Routine `RENDER` and `RERENDER` do not create Google Docs; the app surface still exposes one render path.
