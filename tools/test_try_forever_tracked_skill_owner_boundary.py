#!/usr/bin/env python3

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class TrackedSkillOwnerBoundaryTest(unittest.TestCase):
    def test_existing_owner_observes_exact_candidate_set_before_content_authority_work(self):
        source = inspect.getsource(probe.discover_skills)

        observation = source.index(
            "tracked_observation = observe_tracked_skill_candidates(repo_root, relative_candidates)"
        )
        authority = source.index("tracked_authority = require_tracked_skill_candidates(")
        content_loop = source.index("records: list[SkillRecord] = []")

        self.assertLess(observation, authority)
        self.assertLess(authority, content_loop)

    def test_unavailable_tracked_observation_fails_whole_candidate_set_closed(self):
        source = inspect.getsource(probe.discover_skills)
        self.assertIn('tracked_observation.status != "OBSERVED"', source)
        self.assertIn('error_type="TrackedSkillObservationUnavailable"', source)
        self.assertIn("partial repository-skill authority is forbidden", source)

    def test_untracked_candidate_fails_whole_candidate_set_closed(self):
        source = inspect.getsource(probe.discover_skills)
        self.assertIn('tracked_authority.status != "STABLE"', source)
        self.assertIn('error_type="UntrackedSkillCandidate"', source)
        self.assertIn("tracked_authority.untracked_paths", source)

    def test_owner_imports_existing_organs_instead_of_duplicating_git_logic(self):
        source = inspect.getsource(probe)
        self.assertIn(
            "from try_forever_tracked_skill_observation import observe_tracked_skill_candidates",
            source,
        )
        self.assertIn(
            "from try_forever_skill_tracked_authority import require_tracked_skill_candidates",
            source,
        )
        self.assertNotIn('subprocess.run(\n            ["git", "ls-files"', source)


if __name__ == "__main__":
    unittest.main()
