# THECAULDRON Pocket TTS section renderer

This optional backend renders the same immutable Home Center section requests as the phone worker. It returns WAV bytes over the existing SSH Axis and never controls Android playback.

Install from the phone and enable continuity-safe `auto` routing with one command:

```sh
sh tools/start_cauldron_pocket_tts.sh
```

For a manual installation on THECAULDRON from a reviewed checkout:

```powershell
.\workers\cauldron_pocket_tts_worker\bootstrap.ps1
```

On the phone, select routing without restarting Home Center:

```sh
sh tools/home_center_pocket_tts.sh auto
# or strict remote rendering:
sh tools/home_center_pocket_tts.sh cauldron
# return to phone rendering:
sh tools/home_center_pocket_tts.sh local
```

`auto` is the continuity mode: it tries THECAULDRON and falls back to local Pocket TTS when SSH or the remote renderer is unavailable. Existing cached sections keep playing through the same continuous AudioTrack while either backend produces later sections.

The renderer is outbound-command only: no Windows service, scheduler, inbound HTTP listener, cloud TTS fallback, or voice substitution is installed.
