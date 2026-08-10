#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='glasshouse-test-') as td:
    tmp=Path(td)
    os.environ['HC_GLASSHOUSE_STATE']=str(tmp/'state')
    os.environ['HC_GLASSHOUSE_WORKSPACE']=str(tmp/'workspace')
    (tmp/'workspace').mkdir()
    target=tmp/'workspace'/'hello.py'
    target.write_text('print("glasshouse")\n')
    spec=importlib.util.spec_from_file_location('glasshouse_under_test',ROOT/'tools/glasshouse.py')
    mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)
    event=mod.append_event('file',pane='code',title='hello.py',path=str(target),source='contract')
    assert event['pane']=='code'
    assert mod.load_state()['focus']=='code'
    assert mod.resolve_visible_path(str(target),tmp/'workspace')==target.resolve()
    events=mod.tail_events(10)
    assert events and events[-1]['id']==event['id']
    state=mod.load_state(); state['pins']=['code']; mod.save_state(state)
    assert mod.load_state()['pins']==['code']
print(json.dumps({'ok':True,'contract':'glasshouse.local.v1'}))
