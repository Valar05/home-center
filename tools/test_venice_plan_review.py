#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import venice_plan_review as plan

v,d,f,j = plan.parse_plan_review("VERDICT: PASS\nDIRECTIVE: PLAN_ALLOWED\nJAR: mission boundary\nNOTE: proceed")
assert v == "PASS" and d == "PLAN_ALLOWED" and not f and j == ["mission boundary"]

v,d,f,j = plan.parse_plan_review("VERDICT: FAIL\nDIRECTIVE: REPLAN_REQUIRED\nJAR: evidence truth\nFINDING: no runtime evidence\nNOTE: replan")
assert v == "FAIL" and d == "REPLAN_REQUIRED" and f == ["no runtime evidence"]

v,d,f,j = plan.parse_plan_review("VERDICT: PASS\nDIRECTIVE: REPLAN_REQUIRED\nJAR: mission boundary\nNOTE: contradiction")
assert v == "FAIL" and d == "HALT_REQUIRED" and "inconsistent_plan_pass_directive" in f

skill = (ROOT / "skills/fortress-plan-gate/SKILL.md").read_text(encoding="utf-8")
for token in [
    "RESEARCH",
    "PLAN",
    "SELECT JUDGMENT JARS",
    "ANTAGONIZE",
    "VENICE PLAN REVIEW",
    "PLAN_ALLOWED",
    "REPLAN_REQUIRED",
    "selected jars and rationale",
    "Research. Plan. Pick the jars you need. Attack the plan. Ask Venice. Then execute.",
]:
    assert token in skill, token

source = (ROOT / "tools/venice_plan_review.py").read_text(encoding="utf-8")
for token in [
    "--research-file",
    "--plan-file",
    "--antagonism-file",
    "--jar-file",
    "selectedJudgmentJars",
    "jarSelectionRationale",
    "reviewerPrecedentSha256",
    "planPermissionGranted",
    "venice_review_memory.persist_review",
]:
    assert token in source, token

print("Venice pre-execution plan gate contract: PASS")
