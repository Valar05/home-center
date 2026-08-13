import json, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import swarm


class LocalSwarmTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); self.db=swarm.connect(self.root/"swarm.sqlite3"); swarm.initialize(self.db,100)
        self.id1=self.root/"d1.identity"; self.d1=swarm.register_dispatcher(self.db,"d1",self.id1,101); swarm.activate_dispatcher(self.db,self.d1["generation"],self.id1,30,102)
    def tearDown(self): self.db.close(); self.temp.cleanup()
    def enqueue(self,key="k1",safe=True,at=103): return swarm.enqueue(self.db,key,"NS",[sys.executable,"-c","print('ok')"],{"feature":"swarm"},safe,3,0,at)

    def test_ns_is_opaque_and_unresolved_routes_fail(self):
        job=self.enqueue(); self.assertEqual(job["lane"],"NS"); self.assertIsNone(swarm.status(self.db)["ns_expansion"])
        with self.assertRaises(swarm.SwarmError): swarm.enqueue(self.db,"bad","MADE_UP",["true"],at=103)

    def test_enqueue_is_idempotent_and_conflict_fails(self):
        one=self.enqueue(); two=self.enqueue(); self.assertEqual(one["job_id"],two["job_id"])
        with self.assertRaises(swarm.SwarmError): swarm.enqueue(self.db,"k1","NS",["false"],at=104)

    def test_claims_do_not_duplicate(self):
        self.enqueue("a"); self.enqueue("b",at=104)
        a=swarm.claim(self.db,1,self.id1,"w1",10,105); b=swarm.claim(self.db,1,self.id1,"w2",10,105)
        self.assertNotEqual(a["job_id"],b["job_id"])

    def test_live_cutover_keeps_old_lease_and_moves_new_work(self):
        old_job=self.enqueue("old"); self.enqueue("new",at=104)
        leased=swarm.claim(self.db,1,self.id1,"old-worker",30,105)
        self.id2=self.root/"d2.identity"; d2=swarm.register_dispatcher(self.db,"d2",self.id2,106)
        cut=swarm.activate_dispatcher(self.db,d2["generation"],self.id2,20,107); self.assertEqual(cut["draining_generation"],1)
        with self.assertRaises(swarm.SwarmError): swarm.claim(self.db,1,self.id1,"late",10,108)
        successor=swarm.claim(self.db,2,self.id2,"new-worker",10,108); self.assertNotEqual(successor["job_id"],leased["job_id"])
        receipt=swarm.complete(self.db,leased["job_id"],leased["lease_token"],"old-worker",b"old-result",0,109)
        self.assertEqual(receipt["dispatcher_generation"],1); self.assertEqual(self.db.execute("SELECT state FROM jobs WHERE job_id=?",(leased["job_id"],)).fetchone()[0],"SUCCEEDED")

    def test_expired_safe_work_reclaims_with_higher_token_and_fences_old(self):
        self.enqueue(); first=swarm.claim(self.db,1,self.id1,"w1",5,105); recovered=swarm.recover(self.db,111); self.assertEqual(recovered[0]["state"],"RETRY_WAIT")
        second=swarm.claim(self.db,1,self.id1,"w2",5,120); self.assertGreater(second["lease_token"],first["lease_token"])
        with self.assertRaises(swarm.SwarmError): swarm.complete(self.db,first["job_id"],first["lease_token"],"w1",b"late",0,121)

    def test_expired_unsafe_work_waits_for_evidence(self):
        swarm.enqueue(self.db,"unsafe","NS",["true"],retry_safe=False,at=103); j=swarm.claim(self.db,1,self.id1,"w",5,104); out=swarm.recover(self.db,110)
        self.assertEqual(out[0]["state"],"WAITING_EVIDENCE")

    def test_completion_replay_is_idempotent_but_changed_result_fails(self):
        self.enqueue(); j=swarm.claim(self.db,1,self.id1,"w",30,104); one=swarm.complete(self.db,j["job_id"],j["lease_token"],"w",b"same",0,105); two=swarm.complete(self.db,j["job_id"],j["lease_token"],"w",b"same",0,106); self.assertEqual(one["receipt_id"],two["receipt_id"])
        with self.assertRaises(swarm.SwarmError): swarm.complete(self.db,j["job_id"],j["lease_token"],"w",b"different",0,106)

    def test_cli_runs_real_local_job_and_survives_process_restart(self):
        db=self.root/"cli.sqlite3"; identity=self.root/"cli.identity"; cli=[sys.executable,str(ROOT/"swarm.py"),"--db",str(db),"--json"]
        def run(*args): return json.loads(subprocess.run(cli+list(args),check=True,text=True,capture_output=True).stdout)
        run("init"); d=run("dispatcher-register","--id","cli","--identity-file",str(identity)); run("dispatcher-activate","--generation",str(d["generation"]),"--identity-file",str(identity)); run("enqueue","--key","cli-job","--lane","NS","--argv-json",json.dumps([sys.executable,"-c","print('alive')"]),"--retry-safe"); receipt=run("run-one","--generation",str(d["generation"]),"--identity-file",str(identity),"--worker","cli-worker"); self.assertEqual(receipt["exit_code"],0); self.assertEqual(run("status")["jobs"],[ ] if False else {"SUCCEEDED":1})


if __name__=="__main__": unittest.main()
