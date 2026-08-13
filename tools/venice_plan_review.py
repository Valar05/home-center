#!/usr/bin/env python3
"""Venice pre-execution Judgment-Jar plan review gate.

Primary mode validates and persists a review produced by the active authorized
ChatGPT worker as a distinct adversarial Venice pass. Local Ollama Venice remains
available only by explicit opt-in. The stable legacy wire mode
`judgment_jar_emulation` is retained for compatibility but is the primary mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venice_review
import venice_review_memory

STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "venice"
PLAN_HISTORY = STATE_DIR / "plan-reviews.jsonl"
PLAN_LAST = STATE_DIR / "plan-review-last.json"
PLAN_DIRECTIVES = {"PLAN_ALLOWED", "REPLAN_REQUIRED", "HALT_REQUIRED"}
PRIMARY_REVIEWER_MODE = venice_review.PRIMARY_REVIEWER_MODE
LOCAL_REVIEWER_MODE = venice_review.LOCAL_REVIEWER_MODE


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_plan_review(text: str):
    vm = re.search(r"(?im)^VERDICT\s*:\s*(PASS|FAIL)\s*$", text)
    dm = re.search(r"(?im)^DIRECTIVE\s*:\s*(PLAN_ALLOWED|REPLAN_REQUIRED|HALT_REQUIRED)\s*$", text)
    findings, jars = [], []
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"(?i)^FINDING\s*:", s): findings.append(s.split(":", 1)[1].strip())
        elif re.match(r"(?i)^JAR\s*:", s): jars.append(s.split(":", 1)[1].strip())
    if not vm: return "FAIL", "HALT_REQUIRED", ["plan_reviewer_output_missing_strict_verdict"], jars
    if not dm: return "FAIL", "HALT_REQUIRED", findings + ["plan_reviewer_output_missing_strict_directive"], jars
    verdict, directive = vm.group(1).upper(), dm.group(1).upper()
    if verdict == "PASS" and directive != "PLAN_ALLOWED": return "FAIL", "HALT_REQUIRED", findings + ["inconsistent_plan_pass_directive"], jars
    if verdict == "FAIL" and directive == "PLAN_ALLOWED": return "FAIL", "HALT_REQUIRED", findings + ["failed_plan_cannot_be_allowed"], jars
    return verdict, directive, findings, jars


def load_selected_jars(paths: list[str]) -> tuple[str, list[dict]]:
    docs, manifest = [], []
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if not p.is_file(): raise RuntimeError(f"selected Judgment Jar missing: {p}")
        text = p.read_text(encoding="utf-8", errors="replace")
        docs.append(f"\n--- SELECTED JAR {p} ---\n{text}")
        manifest.append({"path": str(p), "sha256": sha(text)})
    return "".join(docs), manifest


def build_prompt(commission: str, research: str, plan: str, antagonism: str, jar_text: str, jar_manifest: list[dict], rationale: str, precedent: str, evidence: str) -> str:
    return f"""Execute Venice's mandatory PRE-EXECUTION Judgment Jar plan gate as a distinct adversarial pass. Do not execute the plan. Judge whether it is faithful, researched, bounded, evidence-aware, and likely to produce the commissioned outcome.

The worker must not begin substantive mutation or dispatch until this pass returns PLAN_ALLOWED.

Return exactly:
VERDICT: PASS|FAIL
DIRECTIVE: PLAN_ALLOWED|REPLAN_REQUIRED|HALT_REQUIRED
JAR: <at least one applied criterion>
FINDING: <blocking issue; omit if none>
NOTE: <one sentence>

Commission:
{commission}

Research / authoritative state retrieved:
{research}

Proposed bounded plan:
{plan}

Selected Judgment Jars and rationale:
{json.dumps(jar_manifest, indent=2)}
Rationale: {rationale}
{jar_text or '(no jar text supplied)'}

Antagonism / attack on the plan:
{antagonism}

Durable Venice reviewer precedent:
{precedent}

Evidence identity / capability-state notes:
{evidence}

Judge especially:
- Did the worker actually research material unknowns before planning?
- Does the plan preserve outcome, owner, lane/tool, exclusions, evidence standard, and delivery surface?
- Were relevant Judgment Jars selected intentionally, with rationale?
- Did antagonism identify historical Venice scars that apply?
- Is there any silent substitution, unsafe authority, body-lane bypass, evidence laundering, retry storm, duplicate-side-effect risk, or fake completion path?
- Is the done condition testable on the commissioned surface?
- If code/config mutation is planned, is code review explicitly expected at completion?

Precedent is warning evidence, not proof current state is identical.
"""


def persist(receipt: dict) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with PLAN_HISTORY.open("a", encoding="utf-8") as f: f.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    tmp = PLAN_LAST.with_suffix(".tmp"); tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); tmp.replace(PLAN_LAST)
    return PLAN_LAST


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Venice research/plan/antagonism pre-execution gate")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--commission", required=True)
    ap.add_argument("--research-file", required=True)
    ap.add_argument("--plan-file", required=True)
    ap.add_argument("--antagonism-file", required=True)
    ap.add_argument("--jar-file", action="append", default=[])
    ap.add_argument("--jar-rationale", default="")
    ap.add_argument("--evidence-file")
    ap.add_argument("--review-text-file", help="Primary mode: plan review text produced by active ChatGPT Judgment-Jar Venice")
    ap.add_argument("--reviewer", default="chatgpt-venice-judgment-jar")
    ap.add_argument("--local-venice", action="store_true", help="Explicit opt-in to local Ollama Venice")
    ap.add_argument("--model", default=venice_review.DEFAULT_MODEL)
    ap.add_argument("--ollama", default=venice_review.DEFAULT_OLLAMA)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--receipt")
    args = ap.parse_args(argv)
    if args.local_venice and args.review_text_file: raise RuntimeError("choose primary review text OR --local-venice, not both")

    root = venice_review.repo_root(args.repo)
    research = Path(args.research_file).read_text(encoding="utf-8", errors="replace")
    plan = Path(args.plan_file).read_text(encoding="utf-8", errors="replace")
    antagonism = Path(args.antagonism_file).read_text(encoding="utf-8", errors="replace")
    evidence = Path(args.evidence_file).read_text(encoding="utf-8", errors="replace") if args.evidence_file else "(no additional evidence file)"
    if not research.strip() or not plan.strip() or not antagonism.strip(): raise RuntimeError("research, plan, and antagonism must all be non-empty")
    jar_text, jar_manifest = load_selected_jars(args.jar_file)
    if not jar_manifest: raise RuntimeError("no Judgment Jars selected; record a deliberate jar selection before Venice review")
    precedent = venice_review_memory.render_memory(str(root))
    prompt = build_prompt(args.commission, research, plan, antagonism, jar_text, jar_manifest, args.jar_rationale, precedent, evidence)

    reviewer_mode=PRIMARY_REVIEWER_MODE; reviewer=args.reviewer; model=None; ollama=None; raw=""
    if args.local_venice:
        raw, _ = venice_review.ollama_review(args.ollama, args.model, prompt, args.timeout)
        reviewer_mode=LOCAL_REVIEWER_MODE; reviewer="venice-local"; model=args.model; ollama=args.ollama
    elif args.review_text_file:
        raw=Path(args.review_text_file).read_text(encoding="utf-8", errors="replace")

    if raw.strip():
        verdict, directive, findings, applied = parse_plan_review(raw)
    else:
        verdict, directive, findings, applied = "FAIL", "REPLAN_REQUIRED", ["judgment_jar_plan_review_text_required"], ["Venice is always consulted"]
    allowed = verdict == "PASS" and directive == "PLAN_ALLOWED"
    receipt = {
        "schema":"venice-plan-review-v2-judgment-jar-primary", "createdAtEpoch":int(time.time()),
        "reviewer":reviewer, "reviewerMode":reviewer_mode, "independentReviewPass":True, "independentOfWorker":True,
        "repo":str(root), "commission":args.commission, "commissionSha256":sha(args.commission), "researchSha256":sha(research),
        "planSha256":sha(plan), "antagonismSha256":sha(antagonism), "selectedJudgmentJars":jar_manifest,
        "jarSelectionRationale":args.jar_rationale, "reviewerPrecedentSha256":sha(precedent), "verdict":verdict, "directive":directive,
        "planPermissionGranted":allowed, "veniceReviewGateSatisfied":allowed, "externalReviewGateSatisfied":allowed,
        "findings":findings, "judgmentJarApplied":applied, "reviewText":raw, "model":model, "ollama":ollama,
        "legacyWireModeNote":"judgment_jar_emulation is retained as the stable wire identifier for primary ChatGPT Judgment-Jar Venice; it is not fallback semantics.",
    }
    try:
        learned=venice_review_memory.persist_review(receipt); receipt["durableMemoryEntriesWritten"]=len(learned)
    except Exception as exc:
        receipt["verdict"]="FAIL"; receipt["directive"]="HALT_REQUIRED"; receipt["planPermissionGranted"]=False; receipt["veniceReviewGateSatisfied"]=False; receipt["externalReviewGateSatisfied"]=False
        receipt.setdefault("findings", []).append(f"venice_memory_persist_failed:{type(exc).__name__}:{exc}")
    last=persist(receipt)
    if args.receipt:
        p=Path(args.receipt); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({**receipt,"lastReceipt":str(last)},ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if receipt["planPermissionGranted"] else (1 if receipt["directive"] == "REPLAN_REQUIRED" else 2)


if __name__ == "__main__": raise SystemExit(main())
