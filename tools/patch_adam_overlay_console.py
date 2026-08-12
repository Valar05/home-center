#!/usr/bin/env python3
"""One-shot, idempotent source graft for Adam into the existing operator overlay.

This exists because the overlay is a safety-critical organ: patch exact known seams and
fail rather than replacing the service wholesale or silently redesigning it.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
PROVIDER = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorStateProvider.java"
SERVICE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
DAEMON = ROOT / "tools/vlad_swarm_daemon.py"


def patch(path: Path, old: str, new: str):
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise SystemExit(f"adam-overlay patch seam missing in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


changed = False

changed |= patch(STATE,
    "import android.content.SharedPreferences;\n",
    "import android.content.SharedPreferences;\nimport android.util.Base64;\nimport java.nio.charset.StandardCharsets;\n")
changed |= patch(STATE,
    '    static final String KEY_OVERLAY_Y = "overlay_y";\n',
    '    static final String KEY_OVERLAY_Y = "overlay_y";\n'
    '    static final String KEY_ADAM_REQUEST_ID = "adam_request_id";\n'
    '    static final String KEY_ADAM_REQUEST_MODE = "adam_request_mode";\n'
    '    static final String KEY_ADAM_REQUEST_PAYLOAD_B64 = "adam_request_payload_b64";\n')
changed |= patch(STATE,
    '    static int overlayY(Context context) {\n        return prefs(context).getInt(KEY_OVERLAY_Y, 28);\n    }\n',
    '    static int overlayY(Context context) {\n        return prefs(context).getInt(KEY_OVERLAY_Y, 28);\n    }\n\n'
    '    static long adamRequestId(Context context) {\n        return prefs(context).getLong(KEY_ADAM_REQUEST_ID, 0L);\n    }\n\n'
    '    static String adamRequestMode(Context context) {\n        return prefs(context).getString(KEY_ADAM_REQUEST_MODE, "terminal");\n    }\n\n'
    '    static String adamRequestPayloadB64(Context context) {\n        return prefs(context).getString(KEY_ADAM_REQUEST_PAYLOAD_B64, "");\n    }\n')
changed |= patch(STATE,
    '    static void updateText(Context context, String source, String text, long nowMs) {\n',
    '    static void submitAdamRequest(Context context, String mode, String text, long nowMs) {\n'
    '        String cleanMode = mode == null ? "terminal" : mode.trim().toLowerCase();\n'
    '        if (!(cleanMode.equals("terminal") || cleanMode.equals("chat") || cleanMode.equals("continue") || cleanMode.equals("vlad"))) {\n'
    '            throw new IllegalArgumentException("unsupported Adam mode");\n'
    '        }\n'
    '        String clean = text == null ? "" : text.trim();\n'
    '        if (clean.isEmpty()) return;\n'
    '        if (clean.length() > 12000) clean = clean.substring(0, 12000);\n'
    '        String payload = Base64.encodeToString(clean.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);\n'
    '        prefs(context).edit()\n'
    '                .putLong(KEY_ADAM_REQUEST_ID, Math.max(1L, nowMs))\n'
    '                .putString(KEY_ADAM_REQUEST_MODE, cleanMode)\n'
    '                .putString(KEY_ADAM_REQUEST_PAYLOAD_B64, payload)\n'
    '                .commit();\n'
    '    }\n\n'
    '    static void updateText(Context context, String source, String text, long nowMs) {\n')

changed |= patch(PROVIDER,
    '            "panel_collapsed",\n            "overlay_hidden"\n',
    '            "panel_collapsed",\n            "overlay_hidden",\n            "adam_request_id",\n            "adam_request_mode",\n            "adam_request_payload_b64"\n')
changed |= patch(PROVIDER,
    '                OperatorState.panelCollapsed(getContext()) ? 1 : 0,\n                OperatorState.overlayHidden(getContext()) ? 1 : 0\n',
    '                OperatorState.panelCollapsed(getContext()) ? 1 : 0,\n                OperatorState.overlayHidden(getContext()) ? 1 : 0,\n                OperatorState.adamRequestId(getContext()),\n                OperatorState.adamRequestMode(getContext()),\n                OperatorState.adamRequestPayloadB64(getContext())\n')

changed |= patch(SERVICE,
    'import android.widget.Button;\nimport android.widget.LinearLayout;\n',
    'import android.widget.Button;\nimport android.widget.EditText;\nimport android.widget.LinearLayout;\n')
changed |= patch(SERVICE,
    '    private Button controlButton;\n    private boolean expandedText;\n',
    '    private Button controlButton;\n    private EditText adamInput;\n    private String adamMode = "terminal";\n    private boolean expandedText;\n')
adam_ui = r'''        LinearLayout adamModeRow = new LinearLayout(this);
        adamModeRow.setOrientation(LinearLayout.HORIZONTAL);
        adamModeRow.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        adamModeRow.setPadding(0, dp(6), 0, dp(2));
        adamModeRow.addView(adamModeButton("TERM", "terminal", "Adam terminal executor mode"));
        adamModeRow.addView(adamModeButton("CHAT", "chat", "Adam local chatbot mode"));
        adamModeRow.addView(adamModeButton("CONT", "continue", "Adam Continue consumer mode"));
        adamModeRow.addView(adamModeButton("VLAD", "vlad", "Ask Vlad for a bounded consultation"));

        LinearLayout adamInputRow = new LinearLayout(this);
        adamInputRow.setOrientation(LinearLayout.HORIZONTAL);
        adamInputRow.setGravity(Gravity.CENTER_VERTICAL);

        adamInput = new EditText(this);
        adamInput.setTextColor(Color.WHITE);
        adamInput.setHintTextColor(Color.rgb(155, 165, 182));
        adamInput.setHint("Adam — terminal");
        adamInput.setTextSize(14f);
        adamInput.setSingleLine(false);
        adamInput.setMaxLines(4);
        adamInput.setMinHeight(dp(OverlayUiPolicy.MIN_TOUCH_TARGET_DP));
        adamInput.setPadding(dp(8), dp(4), dp(8), dp(4));
        adamInput.setBackground(background(Color.rgb(32, 35, 42), Color.rgb(78, 88, 105)));
        adamInput.setContentDescription("Adam input. Current mode terminal.");
        adamInputRow.addView(adamInput, new LinearLayout.LayoutParams(
                0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button adamSendButton = button("Send");
        adamSendButton.setContentDescription("Send request to Adam using the selected explicit mode");
        adamSendButton.setOnClickListener(v -> submitAdamRequest());
        adamInputRow.addView(adamSendButton);

'''
changed |= patch(SERVICE,
    '        LinearLayout actionRow = new LinearLayout(this);\n',
    adam_ui + '        LinearLayout actionRow = new LinearLayout(this);\n')
changed |= patch(SERVICE,
    '        details.addView(latest);\n        details.addView(actionRow);\n',
    '        details.addView(latest);\n        details.addView(adamModeRow);\n        details.addView(adamInputRow);\n        details.addView(actionRow);\n')
changed |= patch(SERVICE,
    '        windowParams.width = collapsed ? WindowManager.LayoutParams.WRAP_CONTENT : expandedWidthPx;\n        windowManager.updateViewLayout(root, windowParams);\n',
    '        windowParams.width = collapsed ? WindowManager.LayoutParams.WRAP_CONTENT : expandedWidthPx;\n'
    '        int focusFlags = WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL;\n'
    '        if (collapsed) focusFlags |= WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE;\n'
    '        windowParams.flags = focusFlags;\n'
    '        if (collapsed && adamInput != null) adamInput.clearFocus();\n'
    '        windowManager.updateViewLayout(root, windowParams);\n')
adam_methods = r'''    private Button adamModeButton(String label, String mode, String description) {
        Button value = button(label);
        value.setContentDescription(description);
        value.setOnClickListener(v -> {
            adamMode = mode;
            if (adamInput != null) {
                adamInput.setHint("Adam — " + mode);
                adamInput.setContentDescription("Adam input. Current mode " + mode + ".");
                adamInput.requestFocus();
            }
        });
        return value;
    }

    private void submitAdamRequest() {
        if (adamInput == null) return;
        String text = adamInput.getText().toString().trim();
        if (text.isEmpty()) return;
        OperatorState.submitAdamRequest(this, adamMode, text, System.currentTimeMillis());
        adamInput.setText("");
        adamInput.setHint("Adam — " + adamMode + " • sent");
        adamInput.announceForAccessibility("Sent to Adam " + adamMode);
    }

'''
changed |= patch(SERVICE,
    '    private void recomputeExpandedWidth() {\n',
    adam_methods + '    private void recomputeExpandedWidth() {\n')
changed |= patch(SERVICE,
    '        latest.setContentDescription("Latest ChatGPT message. Tap to expand or collapse text.");\n',
    '        latest.setContentDescription("Latest Home Center or Adam message. Tap to expand or collapse text.");\n')

changed |= patch(DAEMON,
    'import argparse\nimport json\n',
    'import argparse\nimport base64\nimport json\nimport re\n')
changed |= patch(DAEMON,
    'INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))\n',
    'INTERVAL = int(os.environ.get("HC_SWARM_INTERVAL", "30"))\nADAM_POLL_SECONDS = float(os.environ.get("HC_ADAM_POLL_SECONDS", "1.0"))\nOPERATOR_STATE_URI = "content://com.homecenter.operatoroverlay.state/state"\nOPERATOR_RECEIVER = "com.homecenter.operatoroverlay/.OverlayUpdateReceiver"\n')
changed |= patch(DAEMON,
    'def run(cmd, timeout=20):\n    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)\n',
    'def run(cmd, timeout=20, cwd=None):\n    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, cwd=cwd)\n')
adam_daemon = r'''
def _operator_field(raw, name, default=""):
    match = re.search(rf"\b{re.escape(name)}=([^,\n]*)", raw)
    return match.group(1).strip() if match else default


def operator_heartbeat():
    result = rish(
        "am broadcast --receiver-foreground "
        "-a com.homecenter.operatoroverlay.HEARTBEAT "
        f"-n {OPERATOR_RECEIVER}"
    )
    append_receipt({"kind": "adam.overlay.heartbeat", "ok": result["rc"] == 0, "result": result})


def operator_update(text, source):
    command = (
        "am broadcast --receiver-foreground "
        "-a com.homecenter.operatoroverlay.UPDATE "
        f"-n {OPERATOR_RECEIVER} "
        f"--es latestText {shlex.quote(str(text)[:8000])} "
        f"--es source {shlex.quote(str(source)[:80])}"
    )
    return rish(command)


def _last_adam_request_id():
    path = STATE_DIR / "adam-last-request-id"
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def _set_last_adam_request_id(value):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "adam-last-request-id").write_text(str(int(value)) + "\n", encoding="utf-8")


def process_adam_overlay(repo_root):
    query = rish(f"content query --uri {shlex.quote(OPERATOR_STATE_URI)}")
    if query["rc"] != 0:
        return
    raw = query["stdout"]
    request_text = _operator_field(raw, "adam_request_id", "0")
    try:
        request_id = int(request_text or "0")
    except ValueError:
        return
    if request_id <= 0 or request_id <= _last_adam_request_id():
        return

    mode = _operator_field(raw, "adam_request_mode", "terminal")
    payload = _operator_field(raw, "adam_request_payload_b64", "")
    # Claim before execution: a daemon restart must not replay a terminal command.
    _set_last_adam_request_id(request_id)
    try:
        text = base64.b64decode(payload, validate=True).decode("utf-8")
    except Exception as exc:
        event = {"kind": "adam.request", "ok": False, "requestId": request_id, "mode": mode, "error": f"invalid_payload: {exc}"}
        append_receipt(event)
        operator_update(event["error"], f"Adam/{mode}")
        return

    result = run(
        ["python3", str(Path(repo_root) / "tools" / "adam.py"), mode, text, "--cwd", repo_root],
        timeout=240,
        cwd=repo_root,
    )
    display = result["stdout"] or result["stderr"] or f"Adam {mode} exited {result['rc']}"
    try:
        parsed = json.loads(result["stdout"])
        display = parsed.get("response") or parsed.get("stdout") or parsed.get("detail") or parsed.get("error") or display
        if parsed.get("stderr"):
            display = (str(display) + "\n" + str(parsed["stderr"])).strip()
    except Exception:
        pass
    update = operator_update(display, f"Adam/{mode}")
    append_receipt({
        "kind": "adam.request",
        "ok": result["rc"] == 0 and update["rc"] == 0,
        "requestId": request_id,
        "mode": mode,
        "result": result,
        "overlayUpdate": update,
    })

'''
changed |= patch(DAEMON,
    'def process_review_inbox(repo_root):\n',
    adam_daemon + 'def process_review_inbox(repo_root):\n')
changed |= patch(DAEMON,
    'def heartbeat(repo_root):\n    shizuku_ok = phone_health()\n    process_review_inbox(repo_root)\n    append_receipt({"kind": "swarm.heartbeat", "ok": True, "shizuku": shizuku_ok})\n',
    'def heartbeat(repo_root):\n    shizuku_ok = phone_health()\n    operator_heartbeat()\n    process_review_inbox(repo_root)\n    append_receipt({"kind": "swarm.heartbeat", "ok": True, "shizuku": shizuku_ok})\n')
changed |= patch(DAEMON,
    '    while True:\n        try:\n            heartbeat(repo_root)\n        except Exception as exc:\n            append_receipt({"kind": "swarm.error", "ok": False, "error": f"{type(exc).__name__}: {exc}"})\n        if args.once:\n            return 0\n        time.sleep(max(5, args.interval))\n',
    '    next_heartbeat = 0.0\n'
    '    while True:\n'
    '        try:\n'
    '            process_adam_overlay(repo_root)\n'
    '            current = time.monotonic()\n'
    '            if current >= next_heartbeat:\n'
    '                heartbeat(repo_root)\n'
    '                next_heartbeat = current + max(5, args.interval)\n'
    '        except Exception as exc:\n'
    '            append_receipt({"kind": "swarm.error", "ok": False, "error": f"{type(exc).__name__}: {exc}"})\n'
    '        if args.once:\n'
    '            return 0\n'
    '        time.sleep(max(0.25, ADAM_POLL_SECONDS))\n')

print("adam overlay graft:", "changed" if changed else "already applied")
