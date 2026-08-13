#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CLI=ROOT/"tools"/"renee.py"; SHELL=ROOT/"regnet.sh"

def run_cli(*args, home):
    env=dict(os.environ); env["RENEE_QA_HOME"]=str(home)
    return subprocess.run([sys.executable,str(CLI),"--json",*args],cwd=ROOT,env=env,text=True,capture_output=True)

class RegnetCliContract(unittest.TestCase):
    def test_status_keyword(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("status",home=td); self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads(r.stdout)["keyword"],"Regnet QA")
    def test_regnet_shell_entrypoint(self):
        with tempfile.TemporaryDirectory() as td:
            env=dict(os.environ); env["RENEE_QA_HOME"]=td
            r=subprocess.run(["sh",str(SHELL),"--json","status"],cwd=ROOT,env=env,text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads(r.stdout)["keyword"],"Regnet QA")
    def test_pass_writes_receipt_and_routes_to_venice(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","tool exists","--acceptance","repo file present","--failure-path","missing config",home=td); p=json.loads(r.stdout)
            self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(p["verdict"],"PASS"); self.assertFalse(p["can_grant_final_stop"]); self.assertEqual(p["next_gate"],"Venice"); self.assertTrue(Path(p["receipt_path"]).exists())
    def test_tested_requires_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","tests passed","--state","tested","--acceptance","tests pass",home=td); self.assertEqual(r.returncode,2); self.assertTrue(any("tested claim" in x for x in json.loads(r.stdout)["blockers"]))
    def test_external_receipt_counts_as_evidence_without_pretending_to_fetch_it(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","runtime callable","--state","callable","--acceptance","runtime receipt exists","--evidence-ref","phone-ticket:abc123","--failure-path","phone offline",home=td); self.assertEqual(r.returncode,0,r.stderr); p=json.loads(r.stdout); self.assertEqual(p["evidence_refs"],["phone-ticket:abc123"])
    def test_missing_acceptance_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","tool exists",home=td); self.assertEqual(r.returncode,2); self.assertTrue(any("acceptance criterion" in x for x in json.loads(r.stdout)["blockers"]))
    def test_unresolved_forces_revision(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","tool exists","--acceptance","repo file present","--unresolved","cannot reproduce crash",home=td); self.assertEqual(r.returncode,2); self.assertTrue(any("cannot reproduce crash" in x for x in json.loads(r.stdout)["blockers"]))
    def test_synthetic_cannot_claim_actual_regnet(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","Regnet approved","--acceptance","approval attributable","--actual-regnet",home=td); self.assertEqual(r.returncode,2); self.assertTrue(any("Regnet attribution" in x for x in json.loads(r.stdout)["blockers"]))
    def test_drew_recall_cannot_be_laundered_as_direct_renee_statement(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("review","Regnet approved","--acceptance","approval attributable","--actual-regnet","--provenance","DREW_RECALL",home=td); self.assertEqual(r.returncode,2); self.assertTrue(any("DREW_RECALL" in x for x in json.loads(r.stdout)["blockers"]))
    def test_derived_rule_requires_sources(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("record","reachable states count","--provenance","DERIVED_RULE","--source","generalization",home=td); self.assertNotEqual(r.returncode,0)
    def test_direct_precedent_is_queryable(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("record","reachable state is product state","--provenance","RENEE_DIRECT","--source","authorized-chat:123","--tag","failure-path",home=td); self.assertEqual(r.returncode,0,r.stderr); rec=json.loads(r.stdout)
            r=run_cli("precedent","reachable state",home=td); self.assertEqual(json.loads(r.stdout)["matches"][0]["fingerprint"],rec["fingerprint"])
    def test_synthetic_correction_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("correct","rqa-x","wrong","--provenance","SYNTHETIC_RENEE","--source","synthetic",home=td); self.assertNotEqual(r.returncode,0)
    def test_direct_precedent_outranks_recall(self):
        with tempfile.TemporaryDirectory() as td:
            for provenance in ("DREW_RECALL","RENEE_DIRECT"):
                r=run_cli("correct","rqa-x","reachable state","--provenance",provenance,"--source",provenance.lower(),home=td); self.assertEqual(r.returncode,0,r.stderr)
            r=run_cli("precedent","reachable state",home=td); self.assertEqual(json.loads(r.stdout)["matches"][0]["provenance"],"RENEE_DIRECT")
    def test_regress_surfaces_human_scar(self):
        with tempfile.TemporaryDirectory() as td:
            r=run_cli("correct","rqa-x","missed offline mode","--provenance","RENEE_CORRECTION","--source","authorized-chat:456","--regression-target","always inspect offline mode",home=td); self.assertEqual(r.returncode,0,r.stderr)
            r=run_cli("regress",home=td); self.assertEqual(json.loads(r.stdout)["human_regression_targets"][0]["regression_target"],"always inspect offline mode")

if __name__=="__main__": unittest.main()
