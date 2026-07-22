# Drive Voice Split Rendering

Voice Split Rendering is a separate Home Center Drive structure for character-specific narration renders. It uses the existing Drive/Docs reader, the Home Drive Character Voice Orientation Registry, and the Google Doc audio cache. It does not change simple Drive Narrate into automatic character voice routing.

## Owner

What existing tool or system should own this capability?

The existing Home Center Drive/Docs reader owns source document intake, `app/src/main/assets/home_drive_character_voice_registry.md` owns speaker-to-voice orientation, and `GoogleDocAudioLibrary` owns saved section audio manifests. The new folder is only a Drive workspace and plan handoff around those systems.

## Drive Folder

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

## Flow

1. Open a Google Doc in Home Center so the app compiles semantic chunks and ingests structured speaker cues.
2. Tap `VOICE SPLIT` or type `prepare voice split plan`.
3. Home Center creates or reuses the Drive workspace and writes a split plan into `02 Split Plans`.
4. The plan marks each section with source hash, capstone, speaker id, registry voice alias, provider voice alias, fallback role voice, and status.
5. Character-specific chunk generation can only proceed from a resolved plan. Unknown voices stay `needs_voice_assignment`.

## Boundary

Simple Drive Narrate continues to use selected role defaults: narrator, dialogue default, and notes default. Character-specific rendering is a separate Voice Split workflow. No automatic voice interpolation is allowed; the existing voice registry or an explicit selected voice must provide the assignment.
