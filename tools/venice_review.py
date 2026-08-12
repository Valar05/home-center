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

# Portable code-review subset distilled from Venice's Judgment Jar. A caller may
# append project-specific jar law with --judgment-jar-file; absence of that file
# never weakens these defaults.
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
        "options": {"temperature": 0, "num_predict": 900},
        "prompt": prompt,
    }).encode("utf-8")
    req = urllib.request.Request(host + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ollama_unavailable: {exc}") from exc
    return str(data.get("response") or "").strip(), data


def parse_review(text):
    verdict_match = re.search(r"(?im)^VERDICT\s*:\s*(PASS|FAIL)\s*$", text)
    directive_match = re.search(r"(?im)^DIRECTIVE\s*:\s*(STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED)\s*$", text)
    findings = []
    jars = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^FINDING\s*:", stripped):
            findings.append(stripped.split(":", 1)[1].strip())
        elif re.match(r"(?i)^JAR\s*:", stripped):
            jars.append(stripped.split(":", 1)[1].strip())
    if not verdict_match:
        return "FAIL", "HALT_REQUIRED", ["reviewer_output_missing_strict_verdict"], jars
    if not directive_match:
        return "FAIL", "HALT_REQUIRED", findings + ["reviewer_output_missing_strict_directive"], jars
    verdict = verdict_match.group(1).upper()
    directive = directive_match.group(1).upper()
    # PASS is permission to stop. FAIL may require repair or a hard halt, but it
    # may never grant stopping-as-done.
    if verdict == "PASS" and directive != "STOP_ALLOWED":
        return "FAIL", "HALT_REQUIRED", findings + ["inconsistent_pass_directive"], jars
    if verdict == "FAIL" and directive == "STOP_ALLOWED":
        return "FAIL", "HALT_REQUIRED", findings + ["fail_cannot_allow_stop"], jars
    return verdict, directive, findings, jars


def review_prompt(diff, acceptance, checks, truncated, jar_text):
    laws = "\n".join(f"- {x}" for x in DEFAULT_JAR_LAWS)
    extra = jar_text.strip() if jar_text else "(no additional project-specific jar supplied)"
    return f"""You are Venice, an external code reviewer and stopping gate. You did not author this change. Review only the supplied diff against the acceptance criteria and Judgment Jar law. Be conservative and terse. Do not redesign the project.

Your authority in this review is explicit:
- STOP_ALLOWED: the reviewed slice is sufficiently complete and evidenced; the worker may stop this slice. This is the ONLY directive compatible with PASS.
- CONTINUE_REQUIRED: the worker is not done and must continue repairing the SAME commissioned slice. Do not expand scope.
- HALT_REQUIRED: continuing mutation is unsafe or the evidence boundary is broken; stop work and surface the blocker rather than improvising.

A PASS means no blocking correctness, safety, regression, provenance, durability, or acceptance failure remains in the evidence supplied. Insufficient evidence is FAIL. Hard-gate breaches outrank aggregate quality.

Return exactly this shape:
VERDICT: PASS|FAIL
DIRECTIVE: STOP_ALLOWED|CONTINUE_REQUIRED|HALT_REQUIRED
JAR: <one applicable jar criterion per line; at least one>
FINDING: <one blocking issue per line; omit if none>
NOTE: <one short sentence>

DEFAULT JUDGMENT JAR LAW:
{laws}

PROJECT-SPECIFIC JAR:
{extra}

ACCEPTANCE:
{acceptance or '(none supplied; require basic correctness and durability only)'}

DETERMINISTIC CHECKS:
{json.dumps(checks, indent=2)}

DIFF_TRUNCATED: {str(truncated).lower()}

DIFF:
{diff}
"""


def main():
    ap = argparse.ArgumentParser(prog="venice review", description="Judgment-Jar external code-review and stop/continue gate")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="HEAD~1")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--acceptance", default="")
    ap.add_argument("--acceptance-file")
    ap.add_argument("--judgment-jar-file", help="Optional additional project-specific Judgment Jar text")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--ollama", default=DEFAULT_OLLAMA)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--receipt")
    ap.add_argument("--deterministic-only", action="store_true", help="Mechanical checks only; never grants stop permission")
    args = ap.parse_args()

    root = repo_root(args.repo)
    acceptance = args.acceptance
    if args.acceptance_file:
        acceptance = Path(args.acceptance_file).read_text(encoding="utf-8")
    jar_text = ""
    if args.judgment_jar_file:
        jar_text = Path(args.judgment_jar_file).read_text(encoding="utf-8")

    checks, files = deterministic_checks(root, args.base, args.head)
    mechanical_ok = all(c["ok"] for c in checks)
    diff, truncated = compact_diff(root, args.base, args.head)
    review_text = ""
    verdict = "FAIL"
    directive = "HALT_REQUIRED"
    findings = []
    jar_applied = []
    model_meta = {}

    if not mechanical_ok:
        directive = "CONTINUE_REQUIRED"
        findings = [f"deterministic:{c['name']}:{c['detail']}" for c in checks if not c["ok"]]
        jar_applied = ["observable evidence", "failure closes toward autonomy"]
    elif args.deterministic_only:
        directive = "CONTINUE_REQUIRED"
        findings = ["semantic_external_review_not_run"]
        jar_applied = ["unknowns remain unknown"]
    else:
        review_text, model_meta = ollama_review(args.ollama, args.model, review_prompt(diff, acceptance, checks, truncated, jar_text), args.timeout)
        verdict, directive, findings, jar_applied = parse_review(review_text)

    stop_permission = directive == "STOP_ALLOWED" and verdict == "PASS" and mechanical_ok and not args.deterministic_only
    continuation_required = directive == "CONTINUE_REQUIRED"
    halt_required = directive == "HALT_REQUIRED"

    receipt = {
        "schema": "venice-code-review-v2",
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
        "directive": directive,
        "stopPermissionGranted": stop_permission,
        "continuationRequired": continuation_required,
        "haltRequired": halt_required,
        "judgmentJarApplied": jar_applied,
        "findings": findings,
        "reviewText": review_text,
        "createdAtEpoch": int(time.time()),
        "externalReviewGateSatisfied": stop_permission,
    }

    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.receipt:
        path = Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)
    # Exit semantics are intentionally worker-friendly:
    # 0 = Venice permits stopping this slice; 1 = Venice requires continuation;
    # 2 = Venice requires a hard halt/escalation.
    if stop_permission:
        return 0
    if continuation_required:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
