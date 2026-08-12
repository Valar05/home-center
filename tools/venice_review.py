#!/usr/bin/env python3
"""Canonical Judgment-Jar code review and stop/continue gate.

Venice is an external reviewer. Every review loads durable prior reviewer
precedent and every blocking finding is appended to durable Venice memory so
future workers inherit the scar rather than rediscovering the same failure.
"""
from __future__ import annotations

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venice_review_memory

DEFAULT_MODEL = os.environ.get("VENICE_REVIEW_MODEL", "qwen2.5-coder:1.5b")
DEFAULT_OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MAX_DIFF_CHARS = int(os.environ.get("VENICE_REVIEW_MAX_DIFF_CHARS", "28000"))
DEFAULT_JAR_LAWS = [
    "Score observable evidence, not beauty, confidence, effort, or proximity.",
    "Actor before artifact: review what changed and who/what owns the mutation.",
    "Source, inference, canon, and capability state remain separate.",
    "Unknowns remain unknown; insufficient evidence cannot be rounded up to PASS.",
    "Provenance must survive every transformation.",
    "Use the minimum technical authority required for the change.",
    "Failure closes toward autonomy; missing evidence must not trigger improvisation.",
    "Appetite has an invoice: account for compute, persistence, maintenance, and recovery cost.",
    "Aftermath exists: the change needs a recoverable, auditable stopping point.",
    "A hard-gate breach outranks aggregate score, urgency, polish, and sunk cost.",
]
DIRECTIVES = {"STOP_ALLOWED", "CONTINUE_REQUIRED", "HALT_REQUIRED"}


def run(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}")
    return p


def repo_root(path):
    return Path(run(["git", "-C", str(path), "rev-parse", "--show-toplevel"]).stdout.strip())


def git_text(root, *args, check=True):
    return run(["git", "-C", str(root), *args], check=check).stdout


def resolve_commit(root, ref):
    return git_text(root, "rev-parse", f"{ref}^{{commit}}").strip()


def deterministic_checks(root, base_commit, head_commit):
    checks = []
    diff_check = run(["git", "-C", str(root), "diff", "--check", f"{base_commit}..{head_commit}"], check=False)
    checks.append({
        "name": "git_diff_check",
        "ok": diff_check.returncode == 0,
        "detail": (diff_check.stdout + diff_check.stderr).strip()[:4000],
    })
    names = [x for x in git_text(root, "diff", "--name-only", f"{base_commit}..{head_commit}").splitlines() if x.strip()]
    conflict, secrets = [], []
    for name in names:
        try:
            text = git_text(root, "show", f"{head_commit}:{name}")
        except Exception:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.startswith(("<<<<<<<", "=======", ">>>>>>>")):
                conflict.append(f"{name}:{lineno}")
            if re.search(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}", line):
                secrets.append(f"{name}:{lineno}")
    checks.append({"name": "conflict_markers", "ok": not conflict, "detail": ", ".join(conflict[:20])})
    checks.append({"name": "obvious_embedded_secrets", "ok": not secrets, "detail": ", ".join(secrets[:20])})
    return checks, names


def review_diff(root, base_commit, head_commit):
    full = git_text(root, "diff", "--unified=3", "--no-ext-diff", f"{base_commit}..{head_commit}")
    full_hash = hashlib.sha256(full.encode()).hexdigest()
    if len(full) <= MAX_DIFF_CHARS:
        return full, False, full_hash, len(full)
    stat = git_text(root, "diff", "--stat", f"{base_commit}..{head_commit}")
    half = max(1, (MAX_DIFF_CHARS - len(stat) - 200) // 2)
    compact = stat + "\n\n[DIFF TRUNCATED FOR MINIMAL COMPUTE]\n" + full[:half] + "\n...\n" + full[-half:]
    return compact, True, full_hash, len(full)


def ollama_review(host, model, prompt, timeout):
    payload = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 900},
        "prompt": prompt,
    }).encode()
    req = urllib.request.Request(host + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ollama_unavailable: {exc}") from exc
    return str(data.get("response") or "").strip(), data


def parse_review(text):
    vm = re.search(r"(?im)^VERDICT\s*:\s*(PASS|FAIL)\s*$", text)
    dm = re.search(r"(?im)^DIRECTIVE\s*:\s*(STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED)\s*$", text)
    findings, jars = [], []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"(?i)^FINDING\s*:", s):
            findings.append(s.split(":", 1)[1].strip())
        elif re.match(r"(?i)^JAR\s*:", s):
            jars.append(s.split(":", 1)[1].strip())
    if not vm:
        return "FAIL", "HALT_REQUIRED", ["reviewer_output_missing_strict_verdict"], jars
    if not dm:
        return "FAIL", "HALT_REQUIRED", findings + ["reviewer_output_missing_strict_directive"], jars
    verdict, directive = vm.group(1).upper(), dm.group(1).upper()
    if verdict == "PASS" and directive != "STOP_ALLOWED":
        return "FAIL", "HALT_REQUIRED", findings + ["inconsistent_pass_directive"], jars
    if verdict == "FAIL" and directive == "STOP_ALLOWED":
        return "FAIL", "HALT_REQUIRED", findings + ["fail_cannot_allow_stop"], jars
    return verdict, directive, findings, jars


def review_prompt(diff, acceptance, checks, truncated, jar_text, base_commit, head_commit, full_hash, precedent_text=None):
    laws = "\n".join(f"- {x}" for x in DEFAULT_JAR_LAWS)
    extra = jar_text.strip() if jar_text else "(no additional project-specific jar supplied)"
    precedent = precedent_text.strip() if precedent_text else "(no durable Venice review precedent supplied)"
    return f"""You are Venice, an external code reviewer and stopping gate. You did not author this change. Review only the supplied evidence against the acceptance criteria, Judgment Jar law, and durable reviewer precedent. Be conservative and terse. Do not redesign the project.

Authority:
- STOP_ALLOWED: reviewed slice is sufficiently complete and evidenced; worker may stop this slice. ONLY directive compatible with PASS.
- CONTINUE_REQUIRED: worker is not done and must repair the SAME commissioned slice.
- HALT_REQUIRED: continuing mutation is unsafe or evidence/authority is broken; halt rather than improvise.

Return exactly:
VERDICT: PASS|FAIL
DIRECTIVE: STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED
JAR: <at least one criterion>
FINDING: <blocking issue; omit if none>
NOTE: <one sentence>

IMMUTABLE REVIEW IDENTITY:
BASE_COMMIT: {base_commit}
HEAD_COMMIT: {head_commit}
FULL_DIFF_SHA256: {full_hash}

DEFAULT JUDGMENT JAR LAW:
{laws}

PROJECT-SPECIFIC JAR:
{extra}

DURABLE VENICE REVIEW PRECEDENT:
{precedent}

Precedent is a warning, not proof that the current task has the same state. Check current evidence independently. Repeated equivalent failures should be treated as stronger regression evidence.

ACCEPTANCE:
{acceptance or '(none supplied; require basic correctness and durability only)'}

DETERMINISTIC CHECKS:
{json.dumps(checks, indent=2)}

DIFF_TRUNCATED: {str(truncated).lower()}
DIFF:
{diff}
"""


def persist_memory(receipt):
    try:
        return venice_review_memory.persist_review(receipt)
    except Exception as exc:
        # Review memory is required for learning but failure to persist it must
        # fail closed rather than falsifying a successful learning claim.
        receipt.setdefault("findings", []).append(f"venice_memory_persist_failed:{type(exc).__name__}:{exc}")
        receipt["verdict"] = "FAIL"
        receipt["directive"] = "HALT_REQUIRED"
        receipt["stopPermissionGranted"] = False
        receipt["continuationRequired"] = False
        receipt["haltRequired"] = True
        receipt["externalReviewGateSatisfied"] = False
        return []


def main():
    ap = argparse.ArgumentParser(prog="venice review", description="Judgment-Jar external code-review and stop/continue gate")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="HEAD~1")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--acceptance", default="")
    ap.add_argument("--acceptance-file")
    ap.add_argument("--judgment-jar-file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama", default=DEFAULT_OLLAMA)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--receipt")
    ap.add_argument("--deterministic-only", action="store_true")
    args = ap.parse_args()

    root = repo_root(args.repo)
    base_commit = resolve_commit(root, args.base)
    head_commit = resolve_commit(root, args.head)
    acceptance = args.acceptance
    if args.acceptance_file:
        acceptance = Path(args.acceptance_file).read_text(encoding="utf-8")
    jar_text = Path(args.judgment_jar_file).read_text(encoding="utf-8") if args.judgment_jar_file else ""
    checks, files = deterministic_checks(root, base_commit, head_commit)
    mechanical_ok = all(c["ok"] for c in checks)
    diff, truncated, full_hash, full_chars = review_diff(root, base_commit, head_commit)
    precedent_text = venice_review_memory.render_memory(str(root))

    review_text = ""
    verdict = "FAIL"
    directive = "HALT_REQUIRED"
    findings = []
    jar_applied = []
    if not mechanical_ok:
        directive = "CONTINUE_REQUIRED"
        findings = [f"deterministic:{c['name']}:{c['detail']}" for c in checks if not c["ok"]]
        jar_applied = ["observable evidence", "failure closes toward autonomy"]
    elif args.deterministic_only:
        directive = "CONTINUE_REQUIRED"
        findings = ["semantic_external_review_not_run"]
        jar_applied = ["unknowns remain unknown"]
    else:
        prompt = review_prompt(diff, acceptance, checks, truncated, jar_text, base_commit, head_commit, full_hash, precedent_text)
        review_text, _ = ollama_review(args.ollama, args.model, prompt, args.timeout)
        verdict, directive, findings, jar_applied = parse_review(review_text)

    stop = directive == "STOP_ALLOWED" and verdict == "PASS" and mechanical_ok and not args.deterministic_only
    cont = directive == "CONTINUE_REQUIRED"
    halt = directive == "HALT_REQUIRED"
    receipt = {
        "schema": "venice-code-review-v3-memory",
        "reviewer": "venice-local",
        "independentOfChatGPT": True,
        "repo": str(root),
        "base": args.base,
        "head": args.head,
        "baseCommit": base_commit,
        "headCommit": head_commit,
        "files": files,
        "fullDiffSha256": full_hash,
        "fullDiffChars": full_chars,
        "reviewPromptDiffSha256": hashlib.sha256(diff.encode()).hexdigest(),
        "diffTruncated": truncated,
        "deterministicChecks": checks,
        "model": None if args.deterministic_only else args.model,
        "ollama": None if args.deterministic_only else args.ollama,
        "verdict": verdict,
        "directive": directive,
        "stopPermissionGranted": stop,
        "continuationRequired": cont,
        "haltRequired": halt,
        "judgmentJarApplied": jar_applied,
        "findings": findings,
        "reviewText": review_text,
        "createdAtEpoch": int(time.time()),
        "externalReviewGateSatisfied": stop,
        "durableMemoryPath": str(venice_review_memory.MEMORY_PATH),
        "precedentLoaded": precedent_text,
    }
    learned = persist_memory(receipt)
    receipt["durableMemoryEntriesWritten"] = len(learned)
    receipt["durableMemoryFingerprints"] = [x.get("fingerprint") for x in learned]

    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        p = Path(args.receipt)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if receipt["stopPermissionGranted"] else (1 if receipt["continuationRequired"] else 2)


if __name__ == "__main__":
    sys.exit(main())
