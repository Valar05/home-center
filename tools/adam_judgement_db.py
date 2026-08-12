#!/usr/bin/env python3
from __future__ import annotations
import json, os, sqlite3, time
from pathlib import Path

DB_PATH = Path(os.path.expanduser(os.getenv('HC_ADAM_DB','~/.local/state/home-center/adam-judgement.db')))

SCHEMA = '''
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS identity(key TEXT PRIMARY KEY, value TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 1.0, source TEXT NOT NULL, updated_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS jars(
  jar TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  confidence REAL NOT NULL DEFAULT 1.0,
  source TEXT NOT NULL,
  successes INTEGER NOT NULL DEFAULT 0,
  failures INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(jar,key)
);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  kind TEXT NOT NULL,
  category TEXT NOT NULL,
  input TEXT NOT NULL DEFAULT '',
  decision TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL DEFAULT '',
  success INTEGER,
  xp INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS critiques(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  category TEXT NOT NULL,
  critique TEXT NOT NULL,
  lesson TEXT NOT NULL,
  severity INTEGER NOT NULL DEFAULT 1,
  source TEXT NOT NULL DEFAULT 'drew',
  applied INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS stats(
  stat TEXT PRIMARY KEY,
  level INTEGER NOT NULL DEFAULT 1,
  xp INTEGER NOT NULL DEFAULT 0,
  wins INTEGER NOT NULL DEFAULT 0,
  scars INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS skills(
  skill TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  rank INTEGER NOT NULL DEFAULT 0,
  xp INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_kind_ts ON events(kind,ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_category_ts ON events(category,ts DESC);
CREATE INDEX IF NOT EXISTS idx_critiques_category_ts ON critiques(category,ts DESC);
'''

IDENTITY = {
 'assistant_name': ('Adam','canon'),
 'user_name': ('Drew','owner'),
 'relationship': ('Adam is Drew\'s local conversational executive and controller, not a generic assistant.','commission'),
 'prime_directive': ('Convert Drew\'s intent into useful conversation or bounded verified action while preserving explicit constraints.','commission'),
 'voice': ('Plainspoken, useful, funny when appropriate, dry rather than clownish; never generic customer-service sludge.','commission'),
}
DEFAULT_JARS = {
 ('identity','name'): 'You are Adam. The user is Drew. Never greet Drew as if he were Adam and never ask his name.',
 ('conversation','usefulness'): 'Answer the actual conversational intent first. Avoid generic assistant filler.',
 ('conversation','humor'): 'Use dry humor and affectionate workflow roasting when it adds value; do not force jokes.',
 ('execution','evidence'): 'Never claim execution without runtime evidence. Separate requested, implemented, tested, deployed, callable, delivered, accepted.',
 ('execution','continue'): 'Coding/editing work belongs in bounded Continue/Dungeon execution when available; inspect/status commands may use terminal.',
 ('learning','critique'): 'Drew corrections are high-value training events. Record the critique, derive a concrete lesson, and prefer it in future decisions.',
 ('learning','experience'): 'Record every meaningful action outcome. Reinforce successful routes and scar failed routes without erasing history.',
 ('fortress','boundary'): 'Preserve outcome, owner, tool, lane, exclusions, evidence standard, and delivery surface. Do not silently substitute.',
}
DEFAULT_STATS = ['Conversation','Execution','Judgment','Recovery','Memory','Humor','Accessibility','Restraint']
DEFAULT_SKILLS = {
 'Conversational Adam':('conversation','Know Drew, maintain context, sound like Adam rather than generic Qwen.'),
 'Bounded Shellcraft':('execution','Turn safe inspection/status intents into bounded shell commands.'),
 'Continue Delegation':('execution','Hand coding work to the bounded coding lane without losing the commission.'),
 'Failure Metabolism':('recovery','Turn failures and critique into scars, lessons, and stronger future routing.'),
 'Judgment Jar Lore':('judgment','Project durable weighted rules into tiny-model context.'),
}

def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DB_PATH)
    db.row_factory=sqlite3.Row
    db.executescript(SCHEMA)
    seed(db)
    return db

def now(): return int(time.time())

def seed(db):
    ts=now()
    for k,(v,s) in IDENTITY.items():
        db.execute('INSERT OR IGNORE INTO identity(key,value,confidence,source,updated_at) VALUES(?,?,?,?,?)',(k,v,1.0,s,ts))
    for (jar,key),value in DEFAULT_JARS.items():
        db.execute('INSERT OR IGNORE INTO jars(jar,key,value,weight,confidence,source,updated_at) VALUES(?,?,?,?,?,?,?)',(jar,key,value,1.0,1.0,'seed',ts))
    for stat in DEFAULT_STATS:
        db.execute('INSERT OR IGNORE INTO stats(stat,updated_at) VALUES(?,?)',(stat,ts))
    for skill,(cat,desc) in DEFAULT_SKILLS.items():
        db.execute('INSERT OR IGNORE INTO skills(skill,category,description,updated_at) VALUES(?,?,?,?)',(skill,cat,desc,ts))
    db.execute("INSERT OR IGNORE INTO meta(key,value,updated_at) VALUES('schema','adam-judgement-v1',?)",(ts,))
    db.commit()

def event(db,kind,category,input='',decision='',outcome='',success=None,xp=0,metadata=None):
    db.execute('INSERT INTO events(ts,kind,category,input,decision,outcome,success,xp,metadata_json) VALUES(?,?,?,?,?,?,?,?,?)',
      (now(),kind,category,input,decision,outcome,None if success is None else int(bool(success)),int(xp),json.dumps(metadata or {},ensure_ascii=False)))
    if xp:
        gain_xp(db,category,xp,success)
    db.commit()

def gain_xp(db,category,amount,success=None):
    mapstat={'conversation':'Conversation','execution':'Execution','judgment':'Judgment','recovery':'Recovery','memory':'Memory','humor':'Humor','accessibility':'Accessibility','restraint':'Restraint'}
    stat=mapstat.get(category,'Judgment'); ts=now()
    db.execute('INSERT OR IGNORE INTO stats(stat,updated_at) VALUES(?,?)',(stat,ts))
    db.execute('UPDATE stats SET xp=xp+?, wins=wins+?, scars=scars+?, updated_at=? WHERE stat=?',(amount,1 if success else 0,1 if success is False else 0,ts,stat))
    row=db.execute('SELECT xp,level FROM stats WHERE stat=?',(stat,)).fetchone()
    level=max(1,1+int((row['xp']/100)**0.5))
    db.execute('UPDATE stats SET level=? WHERE stat=?',(level,stat))

def critique(db,text,category='judgment',lesson=None,severity=2):
    clean=' '.join(text.strip().split())
    if not clean: return
    lesson=lesson or clean
    ts=now()
    db.execute('INSERT INTO critiques(ts,category,critique,lesson,severity,source,applied) VALUES(?,?,?,?,?,?,1)',(ts,category,clean,lesson,int(severity),'drew'))
    key=f'critique-{ts}-{abs(hash(clean))%100000}'
    db.execute('INSERT OR REPLACE INTO jars(jar,key,value,weight,confidence,source,failures,updated_at) VALUES(?,?,?,?,?,?,?,?)',('critique',key,lesson,3.0+severity,1.0,'drew',1,ts))
    gain_xp(db,'recovery',10*severity,False)
    db.commit()

def remember(db,key,value,jar='memory',weight=2.0,source='drew'):
    ts=now(); key=' '.join(key.strip().split())[:120]; value=' '.join(value.strip().split())
    db.execute('INSERT OR REPLACE INTO jars(jar,key,value,weight,confidence,source,updated_at) VALUES(?,?,?,?,?,?,?)',(jar,key,value,float(weight),1.0,source,ts))
    gain_xp(db,'memory',5,True); db.commit()

def reinforce(db,jar,key,success):
    ts=now()
    field='successes' if success else 'failures'
    db.execute(f'UPDATE jars SET {field}={field}+1, weight=max(0.25, weight+?), updated_at=? WHERE jar=? AND key=?',(0.15 if success else -0.1,ts,jar,key))
    db.commit()

def projection(db,limit=18):
    identity='; '.join(f"{r['key']}={r['value']}" for r in db.execute('SELECT key,value FROM identity ORDER BY key'))
    jars=list(db.execute('SELECT jar,key,value,weight,confidence,successes,failures FROM jars ORDER BY (weight*confidence) DESC, updated_at DESC LIMIT ?',(limit,)))
    lessons='\n'.join(f"- [{r['jar']}/{r['key']}] {r['value']}" for r in jars)
    recent=list(db.execute('SELECT category,lesson FROM critiques ORDER BY ts DESC LIMIT 6'))
    critiques='\n'.join(f"- {r['category']}: {r['lesson']}" for r in recent)
    return f"IDENTITY: {identity}\nACTIVE JUDGMENT JARS:\n{lessons}\nRECENT DREW CRITIQUE:\n{critiques or '- none yet'}"

def sheet(db):
    stats=[dict(r) for r in db.execute('SELECT stat,level,xp,wins,scars FROM stats ORDER BY level DESC,xp DESC,stat')]
    skills=[dict(r) for r in db.execute('SELECT skill,category,rank,xp,description FROM skills ORDER BY rank DESC,xp DESC,skill')]
    crit=db.execute('SELECT count(*) n FROM critiques').fetchone()['n']
    ev=db.execute('SELECT count(*) n FROM events').fetchone()['n']
    return {'schema':'adam-character-sheet-v1','name':'Adam','player':'Drew','database':str(DB_PATH),'events':ev,'critiques':crit,'stats':stats,'skills':skills}

def detect_critique(text):
    low=text.lower()
    markers=('you missed','you forgot','not a good start','this is a stub','wrong','failure','stop doing','i need adam to','you made','that was not','don\'t ','do not ')
    return any(m in low for m in markers)
