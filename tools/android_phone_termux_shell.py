#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import os, re, subprocess
from pathlib import Path

MAX_COMMAND_CHARS=int(os.getenv('HC_PHONE_SHELL_MAX_COMMAND_CHARS','8000'))
MAX_OUTPUT_CHARS=int(os.getenv('HC_PHONE_SHELL_MAX_OUTPUT_CHARS','24000'))
MAX_TIMEOUT_SECONDS=int(os.getenv('HC_PHONE_SHELL_MAX_TIMEOUT_SECONDS','300'))
BASH=os.getenv('PREFIX','/data/data/com.termux/files/usr') + '/bin/bash'

SECRET_PATTERNS=[
    re.compile(r'Bearer\s+[A-Za-z0-9._~+/=-]{12,}',re.I),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{20,}\b'),
    re.compile(r'\bya29\.[A-Za-z0-9._-]{20,}\b'),
    re.compile(r'\bAIza[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'),
    re.compile(r'((?:TOKEN|SECRET|PASSWORD|CREDENTIAL)\s*[=:]\s*["\']?)[^"\'\s]{8,}',re.I),
]


def _redact(value:str)->str:
    text=str(value or '')
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            text=pattern.sub(r'\1[REDACTED]',text)
        else:
            text=pattern.sub('[REDACTED]',text)
    if len(text) > MAX_OUTPUT_CHARS:
        text=text[:MAX_OUTPUT_CHARS] + '\n[TRUNCATED]'
    return text


def execute(action:dict)->dict:
    if str(action.get('action') or '') != 'phone_shell':
        raise ValueError('unsupported Termux shell action')
    command=str(action.get('command') or '').strip()
    if not command:
        raise ValueError('phone_shell requires command')
    if len(command) > MAX_COMMAND_CHARS:
        raise ValueError(f'phone_shell command exceeds {MAX_COMMAND_CHARS} characters')
    timeout=max(1,min(int(action.get('timeoutSeconds') or 60),MAX_TIMEOUT_SECONDS))
    cwd=Path(os.path.expanduser(str(action.get('cwd') or '~'))).resolve()
    if not cwd.exists() or not cwd.is_dir():
        raise ValueError(f'phone_shell cwd is not a directory: {cwd}')
    proc=subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        executable=BASH,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )
    return {
        'ok': proc.returncode == 0,
        'action': 'phone_shell',
        'exitCode': proc.returncode,
        'cwd': str(cwd),
        'stdout': _redact(proc.stdout),
        'stderr': _redact(proc.stderr),
        'timeoutSeconds': timeout,
    }
