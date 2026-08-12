#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ensure=(ROOT/'tools/ensure_venice_local.sh').read_text(encoding='utf-8')
wrap=(ROOT/'tools/venice_review_selfheal.sh').read_text(encoding='utf-8')
assert 'ollama serve' in ensure
assert 'ollama pull' in ensure
assert 'venice_review.py' in wrap
print('Venice self-heal contract: PASS')
