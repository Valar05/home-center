#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = os.environ.get("VENICE_REVIEW_MODEL", "qwen2.5-coder:1.5b")
DEFAULT_OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MAX_DIFF_CHARS = int(os.environ.get("VENICE_REVIEW_MAX_DIFF_CHARS", "28000"))


def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}")
    return p


def repo_root(path):
    p = run(["git", "-C", str(path), "rev-parse", "--show-toplevel"])
    return Path(p.stdout.strip())


def git_text(root, *args, check=True):
    return run(["git", "-C", str(root), *args], check=check).stdout


def deterministic_checks(root, base, head):
    checks = []
    diff_check = run(["git", "-C", str(root), "diff", "--check", f"{base}..{head}"], check=False)
    checks.append({"name": "git_diff_check", "ok": diff_check.returncode == 0, "detail": (diff_check.stdout + diff_check.stderr).strip()[:4000]})

    names = [x for x in git_text(root, "diff", "--name-only", f"{base}..{head}").splitlines() if x.strip()]
    conflict_hits = []
    secret_hits = []
    for name in names:
        try:
            text = git_text(root, "show", f"{head}:{name}")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.startswith(("<<<<<<<", "=======", ">>>>>>>")):
                conflict_hits.append(f"{name}:{lineno}")
            if re.search(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}", line):
                secret_hits.append(f"{name}:{lineno}")
    checks.append({"name": "conflict_markers", "ok": not conflict_hits, "detail": ", ".join(conflict_hits[:20])})
    checks.append({"name": "obvious_embedded_secrets", "ok": not secret_hits, "detail": ", ".join(secret_hits[:20])})
    return checks, names


def compact_diff(root, base, head):
    diff = git_text(root, "diff", "--unified=3", "--no-ext-diff", f"{base}..{head}")
    if len(diff) <= MAX_DIFF_CHARS:
        return diff, False
    stat = git_text(root, "diff", "--stat", f"{base}..{head}")
    half = max(1, (MAX_DIFF_CHARS - len(stat) - 200) // 2)
    compact = stat + "\n\n[DIFF TRUNCATED FOR MINIMAL COMPUTE]\n" + diff[:half] + "\n...\n" + diff[-half:]
    return compact, True


def ollama_review(host, model, prompt, timeout):
    payload = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 700},
        "prompt": prompt,
    }).encode("utf-8")
    req = urllib.request.Request(host + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ollama_unavailable: {exc}") from exc
    return str(data.get("response") or "").strip(), data


def parse_verdict(text):
    m = re.search(r"(?im)^VERDICT\s*:\s*(PASS|FAIL)\s*$", text)
    if not m:
        return "FAIL", ["reviewer_output_missing_strict_verdict"]
    findings = []
    for line in text.splitlines():
        if re.match(r"(?i)^FINDING\s*:", line.strip()):
            findings.append(line.split(":", 1)[1].strip())
    return m.group(1).upper(), findings


def review_prompt(diff, acceptance, checks, truncated):
    return f"""You are Venice, an external code reviewer. You did not author this change. Review only the supplied diff against the stated acceptance criteria. Be conservative and terse. Do not redesign the project. A PASS means you found no blocking correctness, safety, regression, or acceptance failure in the evidence supplied. If evidence is insufficient, FAIL.\n\nReturn exactly this shape:\nVERDICT: PASS|FAIL\nFINDING: <one blocking issue per line; omit if none>\nNOTE: <one short sentence>\n\nACCEPTANCE:\n{acceptance or '(none supplied; require basic correctness only)'}\n\nDETERMINISTIC CHECKS:\n{json.dumps(checks, indent=2)}\n\nDIFF_TRUNCATED: {str(truncated).lower()}\n\nDIFF:\n{diff}\n"""


def main():
    ap = argparse.ArgumentParser(prog="venice review", description="Minimal-compute external code-review gate")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="HEAD~1")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--acceptance", default="")
    ap.add_argument("--acceptance-file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama", default=DEFAULT_OLLAMA)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--receipt")
    ap.add_argument("--deterministic-only", action="store_true", help="Run mechanical checks only; never counts as external semantic PASS")
    args = ap.parse_args()

    root = repo_root(args.repo)
    acceptance = args.acceptance
    if args.acceptance_file:
        acceptance = Path(args.acceptance_file).read_text(encoding="utf-8")

    checks, files = deterministic_checks(root, args.base, args.head)
    mechanical_ok = all(c["ok"] for c in checks)
    diff, truncated = compact_diff(root, args.base, args.head)
    review_text = ""
    verdict = "FAIL"
    findings = []
    model_meta = {}

    if not mechanical_ok:
        findings = [f"deterministic:{c['name']}:{c['detail']}" for c in checks if not c["ok"]]
    elif args.deterministic_only:
        findings = ["semantic_external_review_not_run"]
    else:
        review_text, model_meta = ollama_review(args.ollama, args.model, review_prompt(diff, acceptance, checks, truncated), args.timeout)
        verdict, findings = parse_verdict(review_text)

    receipt = {
        "schema": "venice-code-review-v1",
        "reviewer": "venice-local",
        "independentOfChatGPT": True,
        "repo": str(root),
        "base": args.base,
        "head": args.head,
        "files": files,
        "diffSha256": hashlib.sha256(diff.encode("utf-8")).hexdigest(),
        "diffTruncated": truncated,
        "deterministicChecks": checks,
        "model": None if args.deterministic_only else args.model,
        "ollama": None if args.deterministic_only else args.ollama,
        "verdict": verdict,
        "findings": findings,
        "reviewText": review_text,
        "createdAtEpoch": int(time.time()),
        "externalReviewGateSatisfied": verdict == "PASS" and mechanical_ok and not args.deterministic_only,
    }

    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        path = Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt["externalReviewGateSatisfied"] else 1


if __name__ == "__main__":
    sys.exit(main())
