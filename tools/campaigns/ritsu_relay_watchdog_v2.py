"""Ritsu relay-only supervisor, v2. No GPU/TTS model actions.

Use the existing Tailscale relay and local 127.0.0.1 companion listener.
A named mutex prevents competing supervisor instances within one Windows session.
File RITSU_RELAY_PAUSED explicitly suspends automatic resurrection.
"""
import ctypes
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHONW = ROOT.parent / ".venv" / "Scripts" / "pythonw.exe"
RELAY = ROOT / "relay.py"
PAUSE = ROOT / "RITSU_RELAY_PAUSED"
LOG = ROOT / "relay-watchdog.log"
HOST = "100.68.37.106"
PORT = 19643
ERROR_ALREADY_EXISTS = 183
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def exclusive_instance():
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Local\\RitsuRelayWatchdogV2")
    if not handle:
        raise OSError("CreateMutexW failed")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return None
    return handle


def event(msg):
    try:
        if LOG.exists() and LOG.stat().st_size > 1024 * 1024:
            previous = LOG.with_suffix(".log.previous")
            previous.unlink(missing_ok=True)
            LOG.replace(previous)
        with LOG.open("a", encoding="utf-8") as out:
            out.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def listening():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=2):
            return True
    except OSError:
        return False


def tailnet_ready():
    result = subprocess.run(
        ["tailscale", "ip", "-4"], capture_output=True,
        text=True, timeout=8, creationflags=CREATE_NO_WINDOW
    )
    return result.returncode == 0 and HOST in result.stdout.split()


def main():
    mutex = exclusive_instance()
    if mutex is None:
        return
    event("SUPERVISOR_STARTED")
    backoff = 15
    while True:
        try:
            if PAUSE.exists():
                backoff = 15
                time.sleep(15)
                continue
            if listening():
                backoff = 15
                time.sleep(15)
                continue
            if not tailnet_ready():
                event("TAILSCALE_NOT_READY")
            elif not PYTHONW.exists() or not RELAY.exists():
                event("MISSING_CANONICAL_RELAY")
            else:
                subprocess.Popen(
                    [str(PYTHONW), str(RELAY), "--host", HOST],
                    cwd=str(ROOT), creationflags=CREATE_NO_WINDOW,
                    close_fds=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                event("RELAY_LAUNCH_REQUESTED")
                time.sleep(20)
                if listening():
                    event("RELAY_LISTENING")
                    backoff = 15
                else:
                    event("RELAY_NOT_READY")
                    backoff = min(max(backoff * 2, 30), 300)
        except Exception as exc:
            event("ERROR " + type(exc).__name__)
            backoff = min(max(backoff * 2, 30), 300)
        time.sleep(backoff)


if __name__ == "__main__":
    main()
