#!/usr/bin/env python3
# Anchor-checked, idempotent Spotify radio overlay patcher for authorized bodies.
from __future__ import annotations

import argparse
from pathlib import Path

SERVICE = Path("android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java")
STATE = Path("android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java")
DAEMON = Path("tools/vlad_swarm_daemon.py")
BUILD = Path("android/operator-overlay/app/build.gradle")


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_service(text: str) -> str:
    text = replace_once(
        text,
        '    private EditText adamInput;\n    private String adamMode = "terminal";',
        '    private EditText adamInput;\n'
        '    private String adamMode = "terminal";\n'
        '    private long lastRadioRequestAtMs;',
        "service radio request identity field",
    )
    text = replace_once(
        text,
        '''        titleRow.addView(hideButton);

        details = new LinearLayout(this);''',
        '''        titleRow.addView(hideButton);

        LinearLayout radioRow = new LinearLayout(this);
        radioRow.setOrientation(LinearLayout.HORIZONTAL);
        radioRow.setGravity(Gravity.CENTER_VERTICAL);
        radioRow.setPadding(0, dp(4), 0, dp(2));
        radioRow.setContentDescription("Spotify Radio background controls");

        TextView radioLabel = textView(12f, true);
        radioLabel.setText("SPOTIFY");
        radioLabel.setContentDescription("Spotify Radio");
        radioLabel.setGravity(Gravity.CENTER_VERTICAL);
        radioLabel.setPadding(dp(8), 0, dp(8), 0);
        radioRow.addView(radioLabel, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
        radioRow.addView(radioButton("Prev", "previous", "Play the previous Spotify track"));
        radioRow.addView(radioButton("Play", "toggle", "Play or pause Spotify"));
        radioRow.addView(radioButton("Next", "next", "Skip to the next Spotify track"));
        radioRow.addView(radioButton("Stop", "stop", "Stop Spotify Radio and disable keep rolling"));

        details = new LinearLayout(this);''',
        "service persistent radio row",
    )
    text = replace_once(
        text,
        '''        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));''',
        '''        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));
        adamModeRow.addView(adamModeButton("RADIO", "radio", "Control Spotify Radio with a bounded prompt"));''',
        "service radio prompt mode",
    )
    text = replace_once(
        text,
        '''        root.addView(titleRow);
        root.addView(details);''',
        '''        root.addView(titleRow);
        root.addView(radioRow);
        root.addView(details);''',
        "service radio row placement",
    )
    text = replace_once(
        text,
        '''    private Button adamModeButton(String label, String mode, String description) {''',
        '''    private Button radioButton(String label, String command, String description) {
        Button value = button(label);
        value.setContentDescription(description);
        value.setOnClickListener(v -> submitRadioRequest(command));
        return value;
    }

    private void submitRadioRequest(String command) {
        long now = System.currentTimeMillis();
        long requestId = Math.max(now, lastRadioRequestAtMs + 1L);
        lastRadioRequestAtMs = requestId;
        OperatorState.submitAdamRequest(this, "radio", command, requestId);
        if (adamInput != null) {
            adamInput.setHint("Adam — radio • " + command);
            adamInput.announceForAccessibility("Spotify Radio " + command + " requested");
        }
    }

    private Button adamModeButton(String label, String mode, String description) {''',
        "service radio button helpers",
    )
    return text


def patch_state(text: str) -> str:
    old = '''        if (!(cleanMode.equals("terminal") || cleanMode.equals("chat") || cleanMode.equals("continue") || cleanMode.equals("vlad"))) {'''
    new = '''        if (!(cleanMode.equals("terminal") || cleanMode.equals("chat") || cleanMode.equals("continue") || cleanMode.equals("vlad") || cleanMode.equals("radio"))) {'''
    return replace_once(text, old, new, "operator state radio mode")


def patch_daemon(text: str) -> str:
    text = replace_once(
        text,
        '''OVERLAY_RECOVERY_COOLDOWN = int(os.environ.get("HC_OVERLAY_RECOVERY_COOLDOWN", "120"))''',
        '''OVERLAY_RECOVERY_COOLDOWN = int(os.environ.get("HC_OVERLAY_RECOVERY_COOLDOWN", "120"))
SPOTIFY_RADIO_STABLE = Path(os.environ.get(
    "HC_SPOTIFY_RADIO_SCRIPT",
    "~/.local/lib/home-center/spotify-radio/spotify_radio.py",
)).expanduser()
SPOTIFY_RADIO_STATE = Path(os.environ.get(
    "HC_SPOTIFY_RADIO_STATE",
    "~/.local/state/home-center/spotify-radio/state.json",
)).expanduser()''',
        "daemon Spotify constants",
    )
    text = replace_once(
        text,
        '''def operator_update(text,source):
    return rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.UPDATE "+f"-n {OPERATOR_RECEIVER} --es latestText {shlex.quote(str(text)[:8000])} --es source {shlex.quote(str(source)[:80])}")
def _last_adam_request_id():''',
        '''def operator_update(text,source):
    return rish("am broadcast --receiver-foreground -a com.homecenter.operatoroverlay.UPDATE "+f"-n {OPERATOR_RECEIVER} --es latestText {shlex.quote(str(text)[:8000])} --es source {shlex.quote(str(source)[:80])}")

def _spotify_radio_script(repo_root):
    candidates = [
        SPOTIFY_RADIO_STABLE,
        Path(repo_root)/"tools"/"spotify_radio.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None

def run_spotify_radio(repo_root,text,timeout=120):
    script=_spotify_radio_script(repo_root)
    if not script:
        return {"cmd":[],"rc":2,"stdout":"","stderr":"Spotify Radio runtime is not installed."}
    return run(["python3",str(script),"prompt",text],timeout=timeout,cwd=repo_root)

def ensure_spotify_radio(repo_root):
    script=_spotify_radio_script(repo_root)
    if not script:
        return {"ok":False,"state":"runtime_missing"}
    try:
        state=json.loads(SPOTIFY_RADIO_STATE.read_text(encoding="utf-8")) if SPOTIFY_RADIO_STATE.is_file() else {}
    except Exception:
        state={}
    if state.get("continuous") is not True:
        return {"ok":True,"state":"idle","continuous":False}
    result=run(["python3",str(script),"ensure"],timeout=30,cwd=repo_root)
    ok=result["rc"]==0
    summary={"ok":ok,"state":"running" if ok else "failed","continuous":True,"result":result}
    append_receipt({"kind":"spotify.radio.ensure",**summary})
    return summary

def _last_adam_request_id():''',
        "daemon Spotify helpers",
    )
    text = replace_once(
        text,
        '''    result=run(["python3",str(Path(repo_root)/"tools"/"adam.py"),mode,text,"--cwd",repo_root],timeout=None,cwd=repo_root);display=result["stdout"] or result["stderr"] or f"Adam {mode} exited {result['rc']}"''',
        '''    if mode=="radio":
        result=run_spotify_radio(repo_root,text)
    else:
        result=run(["python3",str(Path(repo_root)/"tools"/"adam.py"),mode,text,"--cwd",repo_root],timeout=None,cwd=repo_root)
    display=result["stdout"] or result["stderr"] or f"Adam {mode} exited {result['rc']}"''',
        "daemon radio request route",
    )
    text = replace_once(
        text,
        '''def heartbeat(repo_root):
    jars=sync_judgment_jars(repo_root);shizuku_ok=phone_health();ssh_ok=ensure_phone_ssh(repo_root);overlay_ok=ensure_operator_overlay(repo_root) if shizuku_ok else False
    if overlay_ok:operator_heartbeat()
    process_review_inbox(repo_root);append_receipt({"kind":"swarm.heartbeat","ok":True,"shizuku":shizuku_ok,"ssh":ssh_ok,"overlay":overlay_ok,"judgmentJars":jars})''',
        '''def heartbeat(repo_root):
    jars=sync_judgment_jars(repo_root);shizuku_ok=phone_health();ssh_ok=ensure_phone_ssh(repo_root);overlay_ok=ensure_operator_overlay(repo_root) if shizuku_ok else False
    if overlay_ok:operator_heartbeat()
    radio=ensure_spotify_radio(repo_root) if shizuku_ok else {"ok":False,"state":"shizuku_unavailable"}
    process_review_inbox(repo_root);append_receipt({"kind":"swarm.heartbeat","ok":True,"shizuku":shizuku_ok,"ssh":ssh_ok,"overlay":overlay_ok,"spotifyRadio":radio,"judgmentJars":jars})''',
        "daemon keepalive continuation",
    )
    return text


def patch_build(text: str) -> str:
    text = replace_once(text, "versionCode 3", "versionCode 4", "overlay versionCode")
    text = replace_once(text, "versionName '1.2.0'", "versionName '1.3.0'", "overlay versionName")
    return text


def write_changed(path: Path, transform) -> bool:
    if not path.is_file():
        raise PatchError(f"missing file: {path}")
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    if before == after:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def apply(root: Path) -> dict:
    root = root.resolve()
    changes = {
        str(SERVICE): write_changed(root / SERVICE, patch_service),
        str(STATE): write_changed(root / STATE, patch_state),
        str(DAEMON): write_changed(root / DAEMON, patch_daemon),
        str(BUILD): write_changed(root / BUILD, patch_build),
    }
    return {
        "ok": True,
        "root": str(root),
        "changed": [path for path, changed in changes.items() if changed],
        "unchanged": [path for path, changed in changes.items() if not changed],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = apply(Path(args.root))
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
