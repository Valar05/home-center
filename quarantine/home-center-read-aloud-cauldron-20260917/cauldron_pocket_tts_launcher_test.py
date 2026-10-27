#!/usr/bin/env python3
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1];script=(root/'tools/start_cauldron_pocket_tts.sh').read_text();installer=(root/'tools/install_cauldron_pocket_tts.py').read_text();backend=(root/'tools/pocket_tts_cauldron_backend.py').read_text()
for required in ('install_cauldron_pocket_tts.py','home_center_read_aloud.sh','CAULDRON_POCKET_TTS_READY'):assert required in script
for required in ('HomeCenterMcp','cauldron_status','pocket_tts_render_v2.py'):assert required in installer
assert 'computer_hands.worker.status' in backend and 'computer_hands.request.create' in backend
assert 'ssh' not in backend.lower() and 'resolve_cauldron_ssh.py' not in script
run=subprocess.run(['sh',str(root/'tools/start_cauldron_pocket_tts.sh'),'dry-run'],cwd=root,text=True,capture_output=True,timeout=15)
assert run.returncode==0 and 'Android playback remains untouched' in run.stdout
print('Cauldron Pocket TTS Home Center launcher contract: OK')
