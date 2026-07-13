# ChatGPT Command Center Connector Retrospective

Type: Home Center / Command Center / ChatGPT web connector retrospective
Date: 2026-07-11
Status: current working conclusion

## Concrete State

The backend is not the current blocker:

- Home Center MCP backend green: `tools/command_center_invokability_evidence/command_center_home_bridge_invokability_foreground-deliverable-home-20260711150135.json`
- Command Center MCP backend green: `tools/command_center_invokability_evidence/command_center_invokability_foreground-deliverable-direct-20260711150136.json`

ChatGPT web did show Command Center connected:

- Screenshot: `tools/chatgpt_connector_evidence/foreground_deliverable_20260711_1501_tap_command/screen.png`
- XML/action evidence: `tools/chatgpt_connector_evidence/foreground_deliverable_20260711_1501_tap_command/window.xml`

That XML showed:

- `Command Center`
- `Connected to dclarke1005@gmail.com`
- `command_center.bucket.put_object`
- `command_center.bucket.get_object`
- `command_center.app_control.*`
- `command_center.browser_sessions.*`

The final no-op ChatGPT prompt was not completed because the Chrome surface was closed/clicked away before result readback.

## Why The Frame Window Was Fragile

The bounded Chrome frame was fragile because it depended on Android window-manager state rather than an app-owned automation surface.

Observed failure modes:

- `am start --windowingMode 5` and task move commands can report `Failed transaction (2147483646)` or create/keep a hidden freeform task instead of a durable foreground browser.
- The Chrome task can remain alive but `visible=false`, while Termux or the launcher owns `mCurrentFocus`.
- Clicking away, opening the keyboard, Codex approval prompts, or returning to Termux can collapse or hide the nested window.
- The visible coordinate space changes between fullscreen, freeform, launcher preview, keyboard-visible states, and settings modals.
- Chrome reuses old tabs and tasks; URL restore may affect a hidden Chrome task instead of the visible one.
- `uiautomator` on ChatGPT/OAuth WebViews is useful but not reliable enough as the only control channel. It can be slow, incomplete, or describe the wrong foreground surface after focus changes.
- OAuth is not one page. It is a multi-origin, multi-surface flow: ChatGPT settings, Command Center/Home Center OAuth, Google account/consent, possible unverified-app screens, and callback return.
- OAuth callbacks can leak into the installed ChatGPT app. That app is the wrong acceptance surface for MCP connector setup.

The key lesson: a frame-in-frame is a useful emergency containment lane, but it is not a durable product workflow. It is too easy for the user, Termux, launcher, keyboard, or Android task manager to change the active surface.

## Better Framing

The right unit is not `current page`.

The right unit is:

```text
human_authorized_foreground_task
```

A foreground task is a durable workflow with expected page transitions, not a single page snapshot.

Example:

```json
{
  "taskKey": "chatgpt.command_center_connector.connect",
  "allowedPackages": ["com.android.chrome"],
  "wrongSurfacePackages": ["com.openai.chatgpt"],
  "allowedOrigins": [
    "https://chatgpt.com",
    "https://accounts.google.com",
    "https://us-central1-home-center-dclar.cloudfunctions.net"
  ],
  "humanGates": [
    "CAPTCHA",
    "login verification",
    "account choice when ambiguous",
    "unapproved consent",
    "payment or purchase",
    "destructive account action"
  ]
}
```

The human authorizes the task. The agent advances the state machine. The human only handles human gates.

## How This Becomes Doable From Base Command Center Chat

Base Command Center chat should be the control plane, not the thing that performs fragile Android clicks directly.

Target architecture:

```text
ChatGPT web with Command Center connected
  -> command_center_operation
    -> foreground task record in Home Center cloud
      -> paired Android worker receives task
        -> Android Chrome foreground task actuator
          -> observe/action/evidence loop
            -> app_control.record_run
            -> browser_sessions.record_episode
            -> optional browser_discoveries candidate
```

Command Center chat should be able to do this:

1. Create a foreground task:
   - task key
   - allowed origins/packages
   - target URL or starting instruction
   - human gates
   - max burst time
   - max UI actions
2. Wake the paired Android worker.
3. Ask the human to foreground or approve the target flow.
4. Let the worker run a rapid burst.
5. Store the result, blocker, evidence, and learned selectors.
6. Resume from cloud state if the human clicks away.

The missing product capability is a Command Center operation like:

```text
app_control.request_foreground_task
```

with a paired Android worker that can poll or receive the task and execute it. Termux scripts can prototype this, but they should not be the steady-state runtime.

## Required Worker Behavior

The Android worker should:

- Run on device, not unauthenticated cloud.
- Be paired to Home Center/Command Center.
- Use Shizuku or AccessibilityService for foreground control.
- Take screenshot before XML.
- Verify package, URL/title/page signature, and expected state before every action burst.
- Batch actions instead of one shell command per click.
- Stop on focus loss or unexpected origin.
- Resume from cloud task state after interruption.
- Record every meaningful observation to Home Center cloud.

The worker should not:

- Depend on Codex approval prompts while the web surface is live.
- Require frame-in-frame for an explicitly authorized foreground task.
- Treat coordinates as the durable automation strategy.
- Treat prompt text in ChatGPT as proof that tools worked.
- Store secrets, tokens, cookies, payment data, or raw sensitive form values.

## Command Center Chat Acceptance Test

The minimum real acceptance test is:

1. In ChatGPT web, Command Center is connected.
2. ChatGPT calls `command_center.bucket.put_object`.
3. ChatGPT calls `command_center.bucket.get_object`.
4. The reply includes the created object id, bucket path, and body.

Manual prompt:

```text
Use Command Center tools. Do not answer from memory. Call command_center.bucket.put_object to create a note with kind note.cross_repo, title "ChatGPT foreground hello world", summary "manual no-op proof", body "hello world", projectId "home-center", repository "Valar05/home-center", tags ["manual-chatgpt-proof"], and idempotencyKey "manual-chatgpt-foreground-hello-world-20260711". Then call command_center.bucket.get_object for the created object. Reply only with objectId, path, and body.
```

This proves Command Center in ChatGPT. It does not prove the Android foreground worker until the worker can create and complete a foreground task from Command Center chat.

## Next Build Target

Build the first-class foreground task path:

- Add `app_control.request_foreground_task`.
- Add `app_control.get_foreground_task`.
- Add `app_control.complete_foreground_task`.
- Add Android worker polling or push wakeup.
- Add a Termux-compatible worker prototype that reads the same cloud task records.
- Promote the current Chrome connector learning into that task schema.

Once this exists, the operator flow becomes:

```text
User in Command Center chat:
"Connect/verify the ChatGPT Command Center tools on this phone."

Command Center:
creates foreground task and wakes Android worker.

Phone:
shows "Start authorized foreground task".

Human:
taps start and handles human gates only.

Worker:
runs the fast state-machine flow and records proof.
```
