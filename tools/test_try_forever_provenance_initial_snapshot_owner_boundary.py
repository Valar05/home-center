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

        before_index = source.index("snapshot_before = observe_repository_emission(repo_root)")
        discovery_index = source.index("skills, discovery_errors = discover_skills(repo_root)")
        after_index = source.index("snapshot_after = observe_repository_emission(repo_root)")
        assessment_index = source.index("snapshot = assess_repository_snapshot(")

        self.assertLess(before_index, discovery_index)
        self.assertLess(discovery_index, after_index)
        self.assertLess(after_index, assessment_index)

    def test_expected_head_binding_uses_certified_snapshot_observation_not_retired_helpers(self):
        source = inspect.getsource(probe.main)
        self.assertIn("observed_head = snapshot.head_after or snapshot.head_before", source)
        self.assertNotIn("observed_head = head_after or head_before", source)

    def test_split_git_helpers_are_retired_from_owner_module(self):
        # Keeping dead unbounded helpers around after owner rewiring would leave a
        # tempting future regression path. The completed source surgery removes
        # the split observation organs rather than merely ceasing to call them.
        self.assertFalse(hasattr(probe, "git_head"))
        self.assertFalse(hasattr(probe, "git_dirty"))
        self.assertFalse(hasattr(probe, "command_text"))


if __name__ == "__main__":
    unittest.main()
