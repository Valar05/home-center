import contextlib,hashlib,io,pathlib,tempfile,unittest
from unittest import mock
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import onego
from pathlib import Path

class Publication(unittest.TestCase):
 def test_copies_atomically_and_reuses_matching_hash(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);private=root/'private';private.mkdir();signed=private/'signed.apk';signed.write_bytes(b'APK mock')
   (root/'storage/downloads').mkdir(parents=True)
   with mock.patch.object(onego,'HOME',root):
    with contextlib.redirect_stdout(io.StringIO()) as c:
     onego.publish(signed);first=onego.receipts['downloads_apk'];onego.publish(signed)
   self.assertEqual(Path(first).read_bytes(),signed.read_bytes())
   self.assertIn('COPY_VERIFIED=PASS',c.getvalue());self.assertIn('INSTALLATION=NOT_ATTEMPTED',c.getvalue())
 def test_colliding_publication_is_preserved_and_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);signed=root/'signed.apk';signed.write_bytes(b'APK mock')
   d=root/'storage/downloads';d.mkdir(parents=True)
   file=d/f'Ritsu-Conversation-Usability-v0.19.5-code25-{hashlib.sha256(signed.read_bytes()).hexdigest()[:12]}.apk';file.write_bytes(b'owner file')
   with mock.patch.object(onego,'HOME',root):
    with self.assertRaisesRegex(onego.Block,'DOWNLOADS_EXISTING_FILENAME_COLLISION'):onego.publish(signed)
   self.assertEqual(file.read_bytes(),b'owner file')
 def test_missing_downloads_does_not_rebuild_or_install(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);signed=root/'signed.apk';signed.write_bytes(b'APK mock')
   with mock.patch.object(onego,'HOME',root):
    with self.assertRaisesRegex(onego.Block,'TERMUX_SHARED_DOWNLOADS_MISSING'):onego.publish(signed)
 def test_etiquette_gate_is_pinned_in_manifest(self):
  p=Path(onego.__file__).resolve().parent
  self.assertIn('Campaign Etiquette',(p/'ETIQUETTE_ENFORCEMENT.md').read_text())
  self.assertIn('CAMPAIGN_ETIQUETTE=REVIEWED_AND_PACKAGED',Path(onego.__file__).read_text())
