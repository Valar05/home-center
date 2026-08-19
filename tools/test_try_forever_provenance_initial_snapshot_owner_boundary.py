#!/usr/bin/env python3

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class InitialSnapshotOwnerBoundaryTest(unittest.TestCase):
    def test_initial_snapshot_uses_existing_bounded_one_process_observer(self):
        source = inspect.getsource(probe.main)

        # Discovery certification must not stitch HEAD and cleanliness together
        # from separate unbounded subprocesses when the repository already owns a
        # bounded byte-safe one-process observation organ.
        self.assertNotIn("git_head(repo_root)", source)
        self.assertNotIn("git_dirty(repo_root)", source)

        # Before-discovery, after-discovery, and final-emission custody are three
        # distinct observations. Reusing the existing observer narrows each
        # observation without pretending the whole interval is atomic.
        self.assertGreaterEqual(source.count("observe_repository_emission(repo_root)"), 3)

    def test_snapshot_assessment_still_compares_two_distinct_observations(self):
        source = inspect.getsource(probe.main)
        self.assertIn("assess_repository_snapshot", source)
        self.assertIn("snapshot_before", source)
        self.assertIn("snapshot_after", source)


if __name__ == "__main__":
    unittest.main()
