import contextlib, io, pathlib, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import onego

class SourceDiscoveryAcceptance(unittest.TestCase):
    def sample(self, folder, identifier, extra=None):
        src=pathlib.Path(folder)/identifier/'project'
        for rel,data in {
            'app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java':'class Main {}',
            'app/src/main/AndroidManifest.xml':'<manifest/>',
            'app/src/main/res/layout/main.xml':'<layout/>',
            'app/build.gradle':'versionCode 21',
            'settings.gradle':'include app'
        }.items():
            p=src/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
        if extra:
            p=src/extra[0];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(extra[1])
        return src

    def test_equivalent_duplicates_are_reconciled_and_select_deterministically(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.sample(td,'20261028-runA')
            b=self.sample(td,'20261028-runB')
            (b.parent/'receipt.json').write_text('other metadata')
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                chosen=onego.choose_accepted_source([b,a])
            self.assertEqual(chosen,a)
            self.assertIn('PROVEN_BUILD_INPUT_EQUIVALENT_COUNT_2',stdout.getvalue())
            self.assertEqual(onego.receipts['accepted_source_candidate_count'],2)

    def test_source_mismatch_preserves_both_and_reports_conflicting_input(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.sample(td,'20261028-runA')
            b=self.sample(td,'20261028-runB')
            p=b/'app/src/main/java/com/homecenter/ritsucontrol/MainActivity.java'
            p.write_text('class Different {}')
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                with self.assertRaisesRegex(onego.Block,'ACCEPTED_SOURCE_REPLICAS_DIFFER_IN_BUILD_INPUTS'):
                    onego.choose_accepted_source([a,b])
            self.assertIn('MainActivity.java',stdout.getvalue())
            self.assertEqual(p.read_text(),'class Different {}')

    def test_extra_relevant_source_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.sample(td,'A')
            b=self.sample(td,'B',('app/src/main/java/com/homecenter/ritsucontrol/Added.java','class Added {}'))
            with self.assertRaises(onego.Block):onego.choose_accepted_source([a,b])

    def test_missing_source_blocks_without_mutation(self):
        with self.assertRaisesRegex(onego.Block,'ACCEPTED_V0191_SOURCE_NOT_FOUND'):
            onego.choose_accepted_source([])

    def test_apk_build_precedes_any_windows_execution(self):
        code=pathlib.Path(onego.__file__).read_text()
        b=code.index('    signed=build_sign(staged,sign)',code.index('def execute()'))
        remote=code.index('    windows_inventory()',code.index('def execute()'))
        self.assertLess(b,remote)

    def test_versioned_release_prevents_android_same_filename_collision(self):
        self.assertEqual(onego.VERSION,'1.3.1')
        self.assertIn('v1.3.1',onego.WIN_INIT)
        self.assertNotIn('v1.3.0',onego.WIN_INIT)

if __name__=='__main__':unittest.main()
