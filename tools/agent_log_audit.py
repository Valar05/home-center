#!/data/data/com.termux/files/usr/bin/python3
import argparse
import re
from pathlib import Path

DEFAULT_LOG_DIR = Path("/storage/emulated/0/Download/HomeCenter/logs")
CHAT_RE = re.compile(r"INFO chat (user|assistant): (.*)$")


def latest_log(log_dir):
    logs = sorted(log_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def parse_turns(path):
    turns = []
    for line in path.read_text(errors="replace").splitlines():
        match = CHAT_RE.search(line)
        if match:
            turns.append((match.group(1), match.group(2).strip()))
    return turns


def looks_truncated(text):
    value = text.strip().lower()
    return value.endswith((" a", " the", " for", " with", " to", " and", " or")) or (
        len(value) < 180 and not value.endswith((".", "!", "?", ":", ")")) and "next step" not in value
    )


def audit(turns):
    failures = []
    previous_user = ""
    for role, text in turns:
        lower = text.lower()
        if role == "user":
            previous_user = text
            continue
        user_lower = previous_user.lower()
        if text.startswith("Welcome back. I restored your last conversation.") or text.startswith("Home Center is ready."):
            continue
        if looks_truncated(text):
            failures.append(("truncation", previous_user, text))
        if any(token in user_lower for token in ["few meal ideas", "ideas", "options", "variants", "brainstorm"]):
            idea_count = len(re.findall(r"(?:^|\s)(?:1\.|2\.|3\.|idea|option)", lower))
            if idea_count < 2 and "three" not in lower:
                failures.append(("brainstorm_plurality", previous_user, text))
            if "tell me the protein, starch, and time limit" in lower:
                failures.append(("generic_help", previous_user, text))
        if "bread" not in user_lower and "butter" not in user_lower and any(token in user_lower for token in ["few meal ideas", "what can i make", "brainstorm"]):
            if any(token in lower for token in ["butterbrot", "butter toast", "seasoned toast"]):
                failures.append(("stale_context", previous_user, text))
        if any(token in user_lower for token in ["recipe", "build me", "make me"]) and "step 1" not in lower:
            failures.append(("missing_recipe_steps", previous_user, text))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Audit Home Center chat logs for known agent failures.")
    parser.add_argument("path", nargs="?", help="Log file path. Defaults to latest HomeCenter log.")
    parser.add_argument("--latest", action="store_true", help="Audit the latest public Home Center log.")
    args = parser.parse_args()

    path = Path(args.path) if args.path else latest_log(DEFAULT_LOG_DIR)
    if path is None or not path.exists():
        print("Home Center agent log audit: no log file found")
        return
    failures = audit(parse_turns(path))
    if failures:
        print(f"Home Center agent log audit found {len(failures)} issue(s) in {path}:")
        for kind, user, assistant in failures:
            print(f"- {kind}: user={user[:90]!r} assistant={assistant[:140]!r}")
        raise SystemExit(1)
    print(f"Home Center agent log audit: OK ({path})")


if __name__ == "__main__":
    main()
