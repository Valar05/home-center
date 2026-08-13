#!/usr/bin/env python3
import subprocess
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import venice_review

def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()

with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    run("git","init",cwd=root)
    run("git","config","user.name","Venice Test",cwd=root)
    run("git","config","user.email","venice@example.invalid",cwd=root)
    (root/"schema.js").write_text("repositoryToken: 'short-lived credential description'\nvalue = 1\n")
    run("git","add","schema.js",cwd=root); run("git","commit","-m","base",cwd=root)
    base=run("git","rev-parse","HEAD",cwd=root)
    (root/"schema.js").write_text("repositoryToken: 'short-lived credential description'\nvalue = 2\n")
    run("git","add","schema.js",cwd=root); run("git","commit","-m","benign",cwd=root)
    benign=run("git","rev-parse","HEAD",cwd=root)
    checks,_=venice_review.deterministic_checks(root,base,benign)
    secret=next(item for item in checks if item["name"]=="obvious_embedded_secrets")
    assert secret["ok"], secret
    (root/"schema.js").write_text("repositoryToken: 'short-lived credential description'\nvalue = 2\napi_key = 'abcdefghijklmnop'\n")
    run("git","add","schema.js",cwd=root); run("git","commit","-m","secret",cwd=root)
    bad=run("git","rev-parse","HEAD",cwd=root)
    checks,_=venice_review.deterministic_checks(root,benign,bad)
    secret=next(item for item in checks if item["name"]=="obvious_embedded_secrets")
    assert not secret["ok"], secret
    assert "schema.js:3" in secret["detail"], secret
print("Venice mutation-scoped secret scan tests passed")
