#!/usr/bin/env python3
"""Behavioral regression tests for the non-destructive Adam phone bootstrap."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "tools" / "bootstrap_adam_phone.sh"


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise AssertionError(
            f"command failed ({proc.returncode}): {argv}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def write_executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def make_origin(base: Path) -> tuple[Path, str]:
    origin = base / "origin.git"
    seed = base / "seed"
    run(["git", "init", "--bare", "--initial-branch=main", str(origin)])
    run(["git", "init", "--initial-branch=main", str(seed)])
    run(["git", "config", "user.email", "fortress-test@example.invalid"], cwd=seed)
    run(["git", "config", "user.name", "Fortress Test"], cwd=seed)
    (seed / "tracked.txt").write_text("origin\n", encoding="utf-8")
    write_executable(
        seed / "tools" / "install_adam_prompt_phone.sh",
        """#!/usr/bin/env bash
set -eu
mkdir -p "$HOME/bin"
cat > "$HOME/bin/adam" <<'SH'
#!/usr/bin/env sh
if [ "${1:-}" = "--help" ]; then exit 0; fi
exit 0
SH
chmod 700 "$HOME/bin/adam"
""",
    )
    run(["git", "add", "."], cwd=seed)
    run(["git", "commit", "-m", "fixture"], cwd=seed)
    run(["git", "remote", "add", "origin", str(origin)], cwd=seed)
    run(["git", "push", "-u", "origin", "main"], cwd=seed)
    head = run(["git", "rev-parse", "HEAD"], cwd=seed).stdout.strip()
    return origin, head


def make_fake_gh(fake_bin: Path) -> None:
    write_executable(
        fake_bin / "gh",
        """#!/usr/bin/env sh
set -eu
if [ "${1:-}" = "repo" ] && [ "${2:-}" = "clone" ] && [ "$#" -eq 4 ]; then
  exec git clone "$TEST_ORIGIN" "$4"
fi
echo "unsupported fake gh invocation" >&2
exit 64
""",
    )


def test_dirty_checkout_and_collision() -> None:
    script = BOOTSTRAP.read_text(encoding="utf-8")
    assert "reset --hard" not in script, "bootstrap must never hard-reset a checkout"
    assert "rm -rf" not in script, "bootstrap must never recursively delete a checkout"
    run(["bash", "-n", str(BOOTSTRAP)])

    with tempfile.TemporaryDirectory(prefix="fortress-bootstrap-") as raw:
        base = Path(raw)
        origin, origin_head = make_origin(base)
        dirty = base / "dirty"
        run(["git", "clone", str(origin), str(dirty)])
        (dirty / "tracked.txt").write_text("DREW-DIRTY-DO-NOT-TOUCH\n", encoding="utf-8")
        (dirty / "untracked.txt").write_text("UNTRACKED-TREASURE\n", encoding="utf-8")
        before_head = run(["git", "rev-parse", "HEAD"], cwd=dirty).stdout.strip()
        before_status = run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=dirty).stdout

        home = base / "home"
        fake_bin = base / "fake-bin"
        fake_bin.mkdir(parents=True)
        (home / "bin").mkdir(parents=True)
        make_fake_gh(fake_bin)
        safe = home / ".local" / "share" / "home-center" / "runtime-source"
        safe_marker = Path(str(safe) + ".managed")
        env = os.environ.copy()
        env.update({
            "HOME": str(home),
            "HC_REPO_ROOT": str(dirty),
            "HC_SAFE_REPO_ROOT": str(safe),
            "HC_REPO": "Valar05/home-center",
            "TEST_ORIGIN": str(origin),
            "PATH": os.pathsep.join([str(fake_bin), str(home / "bin"), env.get("PATH", "")]),
        })

        proc = run(["bash", str(BOOTSTRAP)], env=env)
        assert proc.returncode == 0
        assert (dirty / "tracked.txt").read_text(encoding="utf-8") == "DREW-DIRTY-DO-NOT-TOUCH\n"
        assert (dirty / "untracked.txt").read_text(encoding="utf-8") == "UNTRACKED-TREASURE\n"
        assert run(["git", "rev-parse", "HEAD"], cwd=dirty).stdout.strip() == before_head
        assert run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=dirty).stdout == before_status

        receipt_path = home / ".local" / "state" / "home-center" / "bootstrap" / "latest.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["ok"] is True
        assert receipt["schema"] == "adam-phone-bootstrap-v3"
        assert receipt["repo"] == str(safe)
        assert receipt["sourceCommit"] == origin_head
        assert receipt["sourceMode"] == "isolated-managed-clone"
        assert receipt["userCheckout"] == str(dirty)
        assert receipt["userCheckoutDirtyAtDiscovery"] is True
        assert receipt["preservedUserCheckout"] is True
        assert receipt["isolatedManagedSource"] is True
        assert receipt["destructiveUserResetUsed"] is False
        assert receipt["destructiveUserDeleteUsed"] is False
        assert safe_marker.is_file()
        assert not (safe / ".home-center-bootstrap-managed").exists()
        assert run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=safe).stdout == ""
        assert run(["git", "rev-parse", "HEAD"], cwd=safe).stdout.strip() == origin_head
        assert (home / "bin" / "adam").is_file()

        # A repeat run must reuse/fast-forward the marked source rather than
        # quarantining it as dirty because of its own ownership marker.
        run(["bash", str(BOOTSTRAP)], env=env)
        repeat_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert repeat_receipt["ok"] is True
        assert repeat_receipt["sourceMode"] == "isolated-managed-fast-forward"
        assert not list(safe.parent.glob(safe.name + ".quarantine.*"))
        assert run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=dirty).stdout == before_status

        collision = home / "collision"
        collision.mkdir()
        sentinel = collision / "DREW-OWNS-THIS.txt"
        sentinel.write_text("hands off\n", encoding="utf-8")
        collision_env = env.copy()
        collision_env["HC_SAFE_REPO_ROOT"] = str(collision)
        blocked = run(["bash", str(BOOTSTRAP)], env=collision_env, check=False)
        assert blocked.returncode == 30, (blocked.stdout, blocked.stderr)
        assert sentinel.read_text(encoding="utf-8") == "hands off\n"
        assert list(collision.iterdir()) == [sentinel]
        blocked_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert blocked_receipt["ok"] is False
        assert blocked_receipt["stage"] == "safe_source_collision"
        assert blocked_receipt["destructiveUserResetUsed"] is False
        assert blocked_receipt["destructiveUserDeleteUsed"] is False


if __name__ == "__main__":
    test_dirty_checkout_and_collision()
    print("ADAM_PHONE_BOOTSTRAP_PRESERVE_DIRTY=PASS")
