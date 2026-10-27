#!/usr/bin/env python3
"""Fail closed unless the Sticky Snippets campaign plans all expected failures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "tools/campaigns/ritsu_sticky_contingency_plan.json"
data = json.loads(PLAN.read_text(encoding="utf-8"))
assert data["schema"] == "ritsu.sticky.contingency-plan.v1"
assert data["mission"] and data["authority"].startswith("https://docs.google.com/")
assert data["presentEvidence"]["fullCampaignStatus"] == "BLOCKED_NOT_COMPLETED"
assert not data["presentEvidence"]["lastFullCompile"]["signed"]
assert not data["presentEvidence"]["verifiedPhoneBootstrap"]["installableApk"]
assert data["presentEvidence"]["signingIdentityStatus"] == "unknown"
assert data["presentEvidence"]["installedPackageMetadataStatus"] == "unknown"
gates = {r["id"]: r for r in data["gates"]}
for name in ("preflight", "cloud-compile", "signer-inventory", "release",
             "delivery", "device-acceptance"):
    assert name in gates, name
assert gates["signer-inventory"]["status"] == "UNKNOWN"
assert gates["release"]["status"] == "NOT_RUN"
assert gates["delivery"]["status"] == "NOT_RUN"
branches = {r["id"]: r for r in data["branches"]}
for name in (
    "working-tree-conflict", "git-lfs", "missing-local-sdk",
    "network-or-github-auth", "source-test-lint", "signing-preflight",
    "matching-key-available", "key-exists-on-authorized-device-only",
    "key-irrevocably-lost", "install-app-id-mismatch",
    "version-regression", "install-failure", "migration-backup",
    "runtime-acceptance", "partial-operation",
):
    assert name in branches, name
    branch = branches[name]
    assert all(branch[field] for field in
               ("detect", "recover", "responsibility", "failClosed"))
assert "Never uninstall" in " ".join(data["nonnegotiable"])
assert "preflight presented as fulfillment" in data["terminalOutcomes"]["BLOCKED"]
print("CONTINGENCY_MATRIX=PASS")
print("SIGNED_UPGRADE_COMPLETED=false")
