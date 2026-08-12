#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HC_REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
cd "$ROOT"
python3 tools/test_fortress_phone_resume_contract.py
python3 tools/test_vlad_pixel_mnn_contract.py
python3 tools/test_fortress_phone_evidence.py
python3 tools/test_vlad_overlay_self_heal_contract.py
python3 tools/test_venice_selfheal_contract.py
python3 tools/test_adam_cli_contract.py
python3 tools/test_adam_overlay_contract.py
python3 -m py_compile \
  tools/vlad_swarm_daemon.py \
  tools/vlad_pixel_forge_probe.py \
  tools/stage_vlad_pixel_model_phone.py \
  tools/vlad_pixel_request.py \
  tools/vlad_pixel_generate_mnn_phone.py \
  tools/vlad_pixel_pack.py \
  tools/fortress_collect_phone_evidence.py \
  tools/venice_review.py \
  tools/fortress_venice_loop.py
printf 'FORTRESS LOCAL CONTRACTS PASS\n'
