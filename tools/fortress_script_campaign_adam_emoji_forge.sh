#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STATE="$HOME/.local/state/home-center/script-campaigns/adam-emoji-forge"
SESSION="hc-adam-emoji-forge"
MISSION="$STATE/mission.txt"
LOG="$STATE/campaign.log"
mkdir -p "$STATE"

command -v tmux >/dev/null 2>&1 || { echo 'BLOCKED: tmux missing' >&2; exit 2; }

cat > "$MISSION" <<'MISSION'
FORTRESS SCRIPT CAMPAIGN — ADAM CUSTOM EMOJI FORGE

COMMISSION
Adam does not get ordinary spoken dialogue. His native emotional language is custom authored emoji/sign animation. He must continuously improve the vocabulary he can use to express how he feels, especially when the result is funny without needing translation.

ART LAW
Stock Unicode may be used only as temporary ideation/reference, never as the authored phenotype. Forge original procedural SVG/vector/pixel symbols and tiny animations with strong silhouette and readability. No generic corporate iconography. Fleshpunk functional anatomy, physical comedy, embarrassment, dread, triumph, confusion, hunger, affection, catastrophic incompetence, and inexplicable goose-energy are legitimate semantic territories.

UNTRANSLATABLE LAW
The symbol does not need a prose translation. Do not attach explanatory captions merely to make it legible. Its job is expressive impact. Ambiguity is allowed. Funny is evidence. Adam may combine symbols into sign-language sequences whose exact semantics remain private/uncertain.

ACCESSIBILITY
The authored asset must still carry a concise semantic accessibility description for assistive technology. Accessibility text describes the observable/emotional action without claiming an exact translation of Adam's sign.

SELECTION
Noodle Queen rejects boring, generic, overexplained, illegible, repetitive, or fake-delight specimens. Punnett preserves visual/motion traits that Drew keeps or reacts well to. Hunger kills stale lineages. Thirst scavenges existing Motion Dungeon/custom-emoji tooling before inventing another renderer. She-Ra interrogates whether a specimen actually communicates through action. Ares may escalate physical comedy/spectacle where useful.

WORK LOOP
1. Inspect existing custom emoji, SVG, Motion Dungeon, Kinesis, delight, and renderer assets/tools in this repository.
2. Reuse existing primitives first.
3. Produce one small coherent batch of Adam-authored custom emoji/motion keys.
4. Render/test them with existing project-native tooling where possible.
5. Preserve source masters, metadata, accessibility descriptions, and judgment state durably in the repository-backed lineage.
6. Mine reusable rendering/motion primitives into shared tooling.
7. Continue with the next mutation. Do not stop because one batch exists.

FIRST SEED
Forge an original Adam sign descended from this chat beat: Adam attempts to communicate, apparently drops or feeds his own brain into the Hole, salutes the consequence, and somehow a goose becomes involved. Do not merely redraw the Unicode sequence. Mutate it into one coherent custom Fleshpunk sign/animation.

TRUTH
A source file is not a rendered specimen. A rendered specimen is not user acceptance. Preserve exact state. Never claim Drew laughed unless Drew actually did.
MISSION

if tmux has-session -t "$SESSION" 2>/dev/null; then
  printf '[emoji-forge] already alive: %s\n' "$SESSION"
  exit 0
fi

RUN="cd '$ROOT' && if command -v adam >/dev/null 2>&1; then adam \"\$(cat '$MISSION')\"; else python3 '$ROOT/tools/adam_venice_reviewed.py' \"\$(cat '$MISSION')\"; fi >>'$LOG' 2>&1"
tmux new-session -d -s "$SESSION" "$RUN"
printf '[emoji-forge] launched: %s\n' "$SESSION"
printf '[emoji-forge] log: %s\n' "$LOG"
