#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ensure=(ROOT/'tools/ensure_venice_local.sh').read_text(encoding='utf-8')
wrap=(ROOT/'tools/venice_review_selfheal.sh').read_text(encoding='utf-8')
assert 'ollama serve' in ensure
assert 'ollama pull' in ensure
assert 'venice_review.py' in wrap
assert '--local-venice' in wrap
assert 'local_requested=0' in wrap
assert 'if [ "$local_requested" -eq 1 ]' in wrap
assert 'ensure_venice_local.sh' in wrap
# The compatibility wrapper must never unconditionally start local inference.
assert 'bash "$ROOT/tools/ensure_venice_local.sh"\nexec' not in wrap
print('Venice self-heal explicit-local contract: PASS')
