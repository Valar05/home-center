"""Ritsu Pocket repertoire API watchdog. Starts only the fixed local API, never the relay.

Safety:
- User-controlled RITSU_POCKET_MAINTENANCE inhibits startup.
- One watchdog per Windows session (kernel mutex).
- If ANY process owns the localhost port, do not create competing model loads.
- No credentials printed; no process killing; exponential backoff.
- Does not interfere with dedicated Home Center ticket-worker startup.
"""
import ctypes
import os
import socket
import subprocess
import time
from pathlib import Path

ROOT = Path(r"C:\Users\dclar\Documents\Codex\Venice\PocketTTS")
PAUSE = ROOT / "RITSU_POCKET_MAINTENANCE"
API = ROOT / "ritsu_pocket_repertoire_server_v2.py"
PYTHONW = ROOT / ".venv" / "Scripts" / "pythonw.exe"
LOG = ROOT / "ritsu-pocket-repertoire-supervisor.log"
HOST = "127.0.0.1"
PORT = 10205
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MUTEX_NAME = r"Local\RitsuPocketRepertoireSupervisorV2"


def exclusive_instance():
    if os.name != "nt":
        raise RuntimeError("Windows-only watchdog")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None, 0, MUTEX_NAME)
    if not handle:
        raise OSError("Failed to create Warm watchdog mutex")
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(handle)
        return None
    return handle


def log(event):
    try:
        if LOG.is_file() and LOG.stat().st_size > 1048576:
            old = LOG.with_suffix(".log.previous")
            old.unlink(missing_ok=True)
            LOG.replace(old)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + event + "\n")
    except OSError:
        pass


def listening():
    try:
        with socket.create_connection((HOST, PORT), timeout=2):
            return True
    except OSError:
        return False


def main():
    lock = exclusive_instance()
    if lock is None:
        return
    log("STARTED")
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
            if not PYTHONW.is_file() or not API.is_file():
                log("SOURCE_MISSING")
            else:
                subprocess.Popen(
                    [str(PYTHONW), str(API)],
                    cwd=str(ROOT), creationflags=CREATE_NO_WINDOW,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                )
                log("API_START_REQUESTED")
                time.sleep(20)
                if listening():
                    log("API_PORT_LISTENING")
                    backoff = 15
                else:
                    log("API_NOT_READY")
                    backoff = min(backoff * 2, 300)
        except Exception as err:
            log("ERROR " + type(err).__name__)
            backoff = min(backoff * 2, 300)
        time.sleep(backoff)


if __name__ == "__main__":
    main()
