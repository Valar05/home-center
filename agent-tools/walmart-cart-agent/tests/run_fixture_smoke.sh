#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../../.."
out=".tmp/walmart-cart-agent-review.json"
mkdir -p .tmp
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py build-review \
  --fixture agent-tools/walmart-cart-agent/tests/fixtures/shopping_items.json \
  --mappings agent-tools/walmart-cart-agent/tests/fixtures/accepted_mappings.json \
  --output "$out" \
  --problem-log .tmp/walmart-cart-agent-problems.jsonl > .tmp/walmart-cart-agent-summary.json
python3 -c "import json; from pathlib import Path; review=json.loads(Path('.tmp/walmart-cart-agent-review.json').read_text()); assert review['itemCount']==8, review['itemCount']; assert review['statusCounts']['mapped']==1, review['statusCounts']; assert review['statusCounts']['needs_quantity']==1, review['statusCounts']; items={item['key']: item for item in review['review']}; assert items['ground_beef']['quantity']==2; assert items['ranch']['candidates'][0]['sku']=='12345'; assert 'hot_dogs' in items and 'sausages' in items and 'buns' in items; print('walmart-cart-agent fixture: OK')"
export_dir=".tmp/walmart-cart-agent-export"
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py export \
  --fixture agent-tools/walmart-cart-agent/tests/fixtures/shopping_items.json \
  --mappings agent-tools/walmart-cart-agent/tests/fixtures/accepted_mappings.json \
  --output-dir "$export_dir" \
  --problem-log .tmp/walmart-cart-agent-export-problems.jsonl \
  --no-refresh > .tmp/walmart-cart-agent-export-summary.json
test -s "$export_dir/review-latest.json"
test -s "$export_dir/review-latest.commands.txt"
python3 -c "import json; from pathlib import Path; summary=json.loads(Path('.tmp/walmart-cart-agent-export-summary.json').read_text()); assert summary['itemCount']==8, summary; assert Path(summary['review']).name=='review-latest.json'; assert Path(summary['commands']).name=='review-latest.commands.txt'; print('walmart-cart-agent export fixture: OK')"
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py next-item --review "$out" > .tmp/walmart-cart-agent-next.json
python3 -c "import json; from pathlib import Path; data=json.loads(Path('.tmp/walmart-cart-agent-next.json').read_text()); assert data['item']['key']=='ground_beef', data; assert data['requiredVerification']==['brand','size','quantity']; print('walmart-cart-agent next item: OK')"
python3 agent-tools/walmart-cart-agent/walmart_cart_agent.py verify-item \
  --review "$out" \
  --key ground_beef \
  --brand "Marketside" \
  --size "1 lb" \
  --quantity 2 \
  --sku 67890 \
  --product-url https://www.walmart.com/ip/67890 \
  --commands-output .tmp/walmart-cart-agent-verified.commands.txt > .tmp/walmart-cart-agent-verify.json
test -s .tmp/walmart-cart-agent-verified.commands.txt
python3 -c "import json; from pathlib import Path; review=json.loads(Path('.tmp/walmart-cart-agent-review.json').read_text()); item={item['key']: item for item in review['review']}['ground_beef']; assert item['status']=='verified', item; assert item['verified']['brand']=='Marketside', item; assert item['verified']['size']=='1 lb', item; assert item['verified']['quantity']==2, item; assert 'quantity=2' in item['save_command'], item['save_command']; assert 'brand=Marketside' in item['save_command'], item['save_command']; print('walmart-cart-agent verify item: OK')"
