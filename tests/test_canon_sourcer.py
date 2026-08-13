import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import canon_sourcer as canon


class CanonSourcerTests(unittest.TestCase):
    def config(self):
        return {
            "schema": canon.SCHEMA,
            "maximumPacketCharacters": 4000,
            "sources": [
                {"id":"vanguard","title":"Vanguard canon","classification":"canon","syncPolicy":"always","sourceType":"document","sourceFileId":"v1","entities":["Vanguard"],"keywords":["Zornhau"]},
                {"id":"android","title":"Android canon","classification":"canon","syncPolicy":"always","sourceType":"document","sourceFileId":"a1","entities":["Android 67"],"keywords":["weird"]},
                {"id":"notes","title":"Working notes","classification":"noncanon","syncPolicy":"on_demand","sourceType":"document","sourceFileId":"n1","entities":["Unrelated"],"keywords":["draft"]},
            ],
        }

    def test_rejects_non_always_canon(self):
        value=self.config(); value["sources"][0]["syncPolicy"]="on_demand"
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"config.json"; path.write_text(json.dumps(value),encoding="utf-8")
            with self.assertRaises(canon.CanonError): canon.load_config(path)

    def test_sync_fetches_all_canon_not_unrelated_noncanon(self):
        seen=[]
        def fetch(source):
            seen.append(source["id"]); return {"fileId":source["sourceFileId"],"content":f"# {source['title']}\nbody"}
        with tempfile.TemporaryDirectory() as root:
            result=canon.sync(self.config(),Path(root),fetcher=fetch)
            self.assertTrue(result["canonComplete"])
            self.assertEqual(seen,["vanguard","android"])
            self.assertEqual(result["results"][2]["state"],"not_requested")

    def test_packet_is_selective_and_provenanced(self):
        def fetch(source):
            return {"fileId":source["sourceFileId"],"content":f"# {source['title']}\n{source['id']} fact"}
        with tempfile.TemporaryDirectory() as root:
            cache=Path(root); canon.sync(self.config(),cache,fetcher=fetch)
            packet=canon.packet(self.config(),cache,"Vanguard Zornhau")
            self.assertEqual([x["id"] for x in packet["sources"]],["vanguard"])
            self.assertIn("vanguard fact",packet["text"])
            self.assertRegex(packet["sha256"],r"^[0-9a-f]{64}$")

    def test_canary_contract_keeps_vanguard_victory(self):
        canary=canon.normalize("Vanguard kicks Android 67's ass proper. Android puts up a good fight, improves, and gets weirder.")
        for term in ("vanguard","android","good fight","improves","weirder"):
            self.assertIn(canon.normalize(term),canary)


if __name__=="__main__":
    unittest.main()
