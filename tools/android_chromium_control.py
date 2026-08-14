#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import time
from pathlib import Path
from urllib.parse import urlsplit

from android_phone_hands_bridge import run_rish, ui_dump

PACKAGES = (
    "com.android.chrome",
    "com.chrome.beta",
    "com.chrome.dev",
    "org.chromium.chrome",
)
STATE_DIR = Path.home() / ".local" / "state" / "home-center"
LAST_RECEIPT = STATE_DIR / "android-chromium-control-last.json"
CANARY_RECEIPT = STATE_DIR / "android-chromium-control-canary.json"


def rish(command: str, timeout: float = 20) -> str:
    return str(run_rish(command, timeout=timeout)).strip()


def q(value: str) -> str:
    return shlex.quote(str(value))


def validate_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be absolute http(s)")
    if len(url) > 2048:
        raise ValueError("URL exceeds 2048 characters")
    return url


def package_present(package: str) -> bool:
    out = rish(f"pm path {q(package)} 2>/dev/null || true")
    return out.startswith("package:")


def resolve_package() -> str:
    for package in PACKAGES:
        if package_present(package):
            return package
    raise RuntimeError("no supported Android Chromium package is installed")


def _bounded(value: str, limit: int = 4000) -> str:
    value = str(value or "")
    return value if len(value) <= limit else value[-limit:]


def snapshot(package: str, expected_url: str | None = None) -> dict:
    focus = rish("dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -4")
    pid = rish(f"pidof {q(package)} 2>/dev/null || true")
    task = rish(
        "dumpsys activity activities 2>/dev/null "
        f"| grep -F -A 10 -B 4 -- {q(package)} | head -160"
    )
    exact_task = ""
    if expected_url:
        exact_task = rish(
            "dumpsys activity activities 2>/dev/null "
            f"| grep -F -- {q(expected_url)} | head -8 || true"
        )
    xml = ""
    ui_error = ""
    try:
        xml = ui_dump()
    except Exception as exc:
        ui_error = f"{type(exc).__name__}: {exc}"
    screen_sha = rish("screencap -p | sha256sum | awk '{print $1}'", timeout=20)
    host = urlsplit(expected_url).netloc if expected_url else ""
    package_foreground = package in focus
    exact_url_in_task = bool(expected_url and expected_url in exact_task)
    host_visible_in_ui = bool(host and host.lower() in xml.lower())
    state_observed = package_foreground and (
        expected_url is None or exact_url_in_task or host_visible_in_ui
    )
    return {
        "package": package,
        "pid": pid,
        "foreground": _bounded(focus, 1600),
        "taskExcerpt": _bounded(task),
        "expectedUrl": expected_url or "",
        "exactUrlTaskEvidence": _bounded(exact_task, 1800),
        "packageForeground": package_foreground,
        "exactUrlInTask": exact_url_in_task,
        "hostVisibleInUi": host_visible_in_ui,
        "stateObserved": state_observed,
        "uiSha256": hashlib.sha256(xml.encode("utf-8")).hexdigest() if xml else "",
        "uiError": _bounded(ui_error, 1200),
        "screenSha256": screen_sha,
    }


def persist(receipt: dict, path: Path = LAST_RECEIPT) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def receipt(operation: str, ok: bool, **data) -> dict:
    value = {
        "schema": "fortress.android-chromium-control.v1",
        "operation": operation,
        "ok": bool(ok),
        "atEpochMs": int(time.time() * 1000),
        **data,
    }
    persist(value)
    return value


def status() -> dict:
    package = resolve_package()
    return receipt("status", True, observation=snapshot(package))


def force_stop() -> dict:
    package = resolve_package()
    before = snapshot(package)
    rish(f"am force-stop {q(package)}")
    time.sleep(0.35)
    pid_after = rish(f"pidof {q(package)} 2>/dev/null || true")
    ok = not pid_after.strip()
    return receipt(
        "force-stop",
        ok,
        package=package,
        before=before,
        pidAfter=pid_after,
        recoveredByNextOpen=False,
    )


def open_url(url: str, operation: str = "open") -> dict:
    target = validate_url(url)
    package = resolve_package()
    launch = rish(
        "am start -W -a android.intent.action.VIEW "
        f"-d {q(target)} -p {q(package)}",
        timeout=25,
    )
    time.sleep(0.85)
    observed = snapshot(package, target)
    ok = bool(observed.get("stateObserved"))
    return receipt(
        operation,
        ok,
        package=package,
        requestedUrl=target,
        launchOutput=_bounded(launch, 2400),
        observation=observed,
        verification=(
            "foreground plus exact task URL or visible host"
            if ok
            else "requested browser state was not independently observed"
        ),
    )


def navigate(url: str) -> dict:
    return open_url(url, operation="navigate")


def back() -> dict:
    package = resolve_package()
    before = snapshot(package)
    rish("input keyevent KEYCODE_BACK")
    time.sleep(0.45)
    after = snapshot(package)
    ok = package in after.get("foreground", "")
    return receipt("back", ok, before=before, after=after)


def reload_page() -> dict:
    package = resolve_package()
    before = snapshot(package)
    if not before.get("packageForeground"):
        return receipt("reload", False, error="Chromium is not foreground", before=before)
    rish("input keyevent KEYCODE_REFRESH")
    time.sleep(0.6)
    after = snapshot(package)
    ok = bool(after.get("packageForeground"))
    return receipt(
        "reload",
        ok,
        before=before,
        after=after,
        reloadDispatched=True,
        reloadContentChangeProven=(
            bool(before.get("uiSha256"))
            and bool(after.get("uiSha256"))
            and before.get("uiSha256") != after.get("uiSha256")
        ),
        note="Foreground survival is proven; content reload is only proven when UI hash changes.",
    )


def canary() -> dict:
    nonce = str(int(time.time() * 1000))
    first_url = f"https://example.com/?fortress_phone_canary={nonce}-1"
    second_url = f"https://example.org/?fortress_phone_canary={nonce}-2"

    stopped = force_stop()
    first = open_url(first_url, operation="canary-open-after-death")
    second = navigate(second_url)
    package = second.get("package") or first.get("package") or resolve_package()
    final = snapshot(package, second_url)

    hashes_changed = bool(
        first.get("observation", {}).get("screenSha256")
        and second.get("observation", {}).get("screenSha256")
        and first["observation"]["screenSha256"] != second["observation"]["screenSha256"]
    )
    ok = all(
        [
            stopped.get("ok"),
            first.get("ok"),
            second.get("ok"),
            final.get("stateObserved"),
        ]
    )
    result = {
        "schema": "fortress.android-chromium-canary.v1",
        "operation": "canary",
        "ok": bool(ok),
        "atEpochMs": int(time.time() * 1000),
        "browserDeathRecovery": stopped,
        "firstTransition": first,
        "secondTransition": second,
        "finalObservation": final,
        "screenHashChangedAcrossTransitions": hashes_changed,
        "acceptance": {
            "browserWasForceStopped": bool(stopped.get("ok")),
            "reopenedAfterDeath": bool(first.get("ok")),
            "secondExplicitNavigationObserved": bool(second.get("ok")),
            "finalChromiumStateObserved": bool(final.get("stateObserved")),
        },
    }
    persist(result, CANARY_RECEIPT)
    persist(result, LAST_RECEIPT)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="android-chromium-control")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("force-stop")
    open_parser = sub.add_parser("open")
    open_parser.add_argument("url", nargs="?", default="https://chatgpt.com/")
    nav_parser = sub.add_parser("navigate")
    nav_parser.add_argument("url")
    sub.add_parser("reload")
    sub.add_parser("back")
    sub.add_parser("canary")
    args = parser.parse_args(argv)

    try:
        if args.action == "status":
            result = status()
        elif args.action == "force-stop":
            result = force_stop()
        elif args.action == "open":
            result = open_url(args.url)
        elif args.action == "navigate":
            result = navigate(args.url)
        elif args.action == "reload":
            result = reload_page()
        elif args.action == "back":
            result = back()
        elif args.action == "canary":
            result = canary()
        else:
            raise ValueError(f"unsupported action: {args.action}")
    except Exception as exc:
        result = receipt(
            args.action or "unknown",
            False,
            error=f"{type(exc).__name__}: {exc}",
        )

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
