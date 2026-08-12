#!/usr/bin/env python3
from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import adam_judgement_db as mem
import adam_runtime as runtime

with tempfile.TemporaryDirectory() as td:
    mem.DB_PATH=Path(td)/'adam.db'
    db=mem.connect()
    assert runtime.identity_reflex(db,'hello').startswith('Hey Drew')
    who=runtime.identity_reflex(db,'what is my name?')
    assert 'Drew' in who and 'Adam' in who
    before=mem.sheet(db)
    mem.critique(db,'Do not confuse Drew with Adam.',category='conversation',severity=3)
    mem.event(db,'outcome','execution','test','route','failed',False,5)
    mem.event(db,'outcome','execution','test','route','passed',True,8)
    after=mem.sheet(db)
    projection=mem.projection(db)
    assert after['critiques']==before['critiques']+1
    assert after['scars']>=before['scars']+2
    assert 'Do not confuse Drew with Adam.' in projection
    assert any(s['xp']>0 for s in after['stats'])
    assert any(s['xp']>0 for s in after['skills'])
    assert after['name']=='Adam' and after['player']=='Drew'
    db.close()
print('Adam judgement/RPG runtime contract: PASS')
