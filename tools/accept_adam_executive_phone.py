#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import adam_judgement_db as memory
import adam_runtime as runtime


def main():
    db=memory.connect()
    hello=runtime.identity_reflex(db,'hello')
    who=runtime.identity_reflex(db,'what is my name?')
    sheet=memory.sheet(db)
    projection=memory.projection(db)
    knows=bool(hello and 'Drew' in hello and who and 'Drew' in who and 'Adam' in who)
    sqlite_ok=Path(memory.DB_PATH).exists() and sheet.get('name')=='Adam' and sheet.get('player')=='Drew'
    jars_ok='user_name=Drew' in projection and 'assistant_name=Adam' in projection
    ok=knows and sqlite_ok and jars_ok
    receipt={'schema':'adam-executive-phone-acceptance-v3','ok':ok,'knowsUser':knows,'hello':hello,'identityProbe':who,'database':str(memory.DB_PATH),'sqlite':sqlite_ok,'jarsProjected':jars_ok,'characterSheet':sheet}
    print(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)); db.close(); return 0 if ok else 2

if __name__=='__main__': raise SystemExit(main())
