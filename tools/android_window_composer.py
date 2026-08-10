#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, re, shlex, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
from android_phone_hands_bridge import run_rish

ALIASES={
  'chatgpt':'com.openai.chatgpt',
  'termux':'com.termux',
  'chrome':'com.android.chrome',
  'browser':'com.android.chrome',
  'files':'com.google.android.documentsui',
}

def package_of(value:str)->str:
    v=str(value or '').strip()
    if not v: raise ValueError('app is required')
    return ALIASES.get(v.lower(),v)

def resolve_component(pkg:str)->str:
    # Prefer the package manager's actual launcher resolution over hardcoded activities.
    out=str(run_rish(f"cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER {shlex.quote(pkg)} 2>/dev/null | tail -1")).strip()
    if '/' in out and not out.startswith('No activity'):
        return out
    known={
      'com.openai.chatgpt':'com.openai.chatgpt/.MainActivity',
      'com.termux':'com.termux/com.termux.app.TermuxActivity',
      'com.android.chrome':'com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity',
      'com.google.android.documentsui':'com.google.android.documentsui/.files.FilesActivity',
    }
    if pkg in known: return known[pkg]
    raise RuntimeError(f'could not resolve launch activity for {pkg}')

def shell(cmd:str,timeout:float=20)->str:
    return str(run_rish(cmd,timeout=timeout)).strip()

def status()->dict:
    win=shell("dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -4")
    act=shell("dumpsys activity activities 2>/dev/null | grep -E 'Task\{|mResumedActivity|windowingMode=|mLastPausedActivity' | head -120")
    packages={name:pkg for name,pkg in ALIASES.items() if name in ('chatgpt','termux','chrome','files')}
    present={name:(pkg in act or pkg in win) for name,pkg in packages.items()}
    split=bool(re.search(r'windowingMode=(?:split-screen|3|4)|WINDOWING_MODE_MULTI_WINDOW',act,re.I))
    return {'ok':True,'focus':win,'activityExcerpt':act,'present':present,'splitDetected':split}

def start_component(component:str,mode:int|None=None)->str:
    flag='' if mode is None else f' --windowingMode {int(mode)}'
    return shell(f"am start{flag} -n {shlex.quote(component)}",timeout=25)

def compose(primary:str='chatgpt',secondary:str='termux')->dict:
    p_pkg=package_of(primary); s_pkg=package_of(secondary)
    p_comp=resolve_component(p_pkg); s_comp=resolve_component(s_pkg)
    attempts=[]
    # Android ActivityManager still accepts split-screen windowing modes on builds
    # where WM Shell owns the visual split. Use real tasks/apps; never mirror UI.
    for pmode,smode in ((3,4),(4,3)):
        try:
            a=start_component(p_comp,pmode); b=start_component(s_comp,smode)
            attempts.append({'primaryMode':pmode,'secondaryMode':smode,'primary':a[-1000:],'secondary':b[-1000:]})
            st=status()
            if st['present'].get(primary.lower(),p_pkg in st['activityExcerpt']) and st['present'].get(secondary.lower(),s_pkg in st['activityExcerpt']):
                return {'ok':True,'primary':p_pkg,'secondary':s_pkg,'primaryComponent':p_comp,'secondaryComponent':s_comp,'attempts':attempts,'status':st}
        except Exception as exc:
            attempts.append({'primaryMode':pmode,'secondaryMode':smode,'error':str(exc)})
    raise RuntimeError('native split composition failed: '+json.dumps(attempts)[-3000:])

def focus(app:str)->dict:
    pkg=package_of(app); comp=resolve_component(pkg)
    out=start_component(comp,None)
    return {'ok':True,'app':pkg,'component':comp,'launch':out[-1500:],'status':status()}

def swap(work:str)->dict:
    # Keep ChatGPT as the conversation pane; replace/focus the real work app.
    return compose('chatgpt',work)

def probe()->dict:
    return {
      'ok':True,
      'amWindowing': shell("am help 2>/dev/null | grep -i -A3 -B2 windowing | head -40"),
      'activityHelp': shell("cmd activity help 2>/dev/null | grep -i -E 'task|window|split|multi' | head -80"),
      'wmHelp': shell("wm help 2>/dev/null | grep -i -E 'shell|multi|window|size' | head -80"),
      'status':status(),
    }

def execute(action:dict)->dict:
    kind=str(action.get('action') or '')
    if kind=='window_status': return status()
    if kind=='window_probe': return probe()
    if kind=='window_compose': return compose(str(action.get('primary') or 'chatgpt'),str(action.get('secondary') or 'termux'))
    if kind=='window_focus': return focus(str(action.get('app') or 'chatgpt'))
    if kind=='window_swap': return swap(str(action.get('app') or action.get('work') or 'termux'))
    raise ValueError(f'unsupported window composer action: {kind}')

if __name__=='__main__':
    import sys
    print(json.dumps(execute(json.loads(sys.stdin.read() or '{}')),ensure_ascii=False))
