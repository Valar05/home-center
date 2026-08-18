#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_candidate_topology_owner_probe import classify_owner_source


LEGACY = '''
is_skill_file = (
    entry.name == "SKILL.md" and entry.is_file(follow_symlinks=True)
)
'''

WIRED = '''
class SkillCandidateTopologyError(ValueError):
    pass
if entry.name == "SKILL.md":
    if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
        raise SkillCandidateTopologyError(path)
except SkillCandidateTopologyError as error:
    x = DiscoveryError(error_type=type(error).__name__)
'''


class CandidateTopologyOwnerProbeTest(unittest.TestCase):
    def test_legacy_owner_is_not_promoted(self):
        result = classify_owner_source(LEGACY)
        self.assertEqual("LEGACY_OWNER", result["verdict"])

    def test_fully_wired_owner_requires_all_markers_and_no_legacy_follow_links(self):
        result = classify_owner_source(WIRED)
        self.assertEqual("SOURCE_WIRED", result["verdict"])

    def test_mixed_owner_fails_closed_as_partial_unsafe(self):
        result = classify_owner_source(LEGACY + WIRED)
        self.assertEqual("PARTIAL_UNSAFE", result["verdict"])
        self.assertIn("mixed", result["reason"])

    def test_one_missing_required_marker_is_partial_unsafe(self):
        result = classify_owner_source(WIRED.replace("except SkillCandidateTopologyError as error:\n", ""))
        self.assertEqual("PARTIAL_UNSAFE", result["verdict"])

    def test_unrelated_no_follow_text_does_not_count_as_full_wiring(self):
        result = classify_owner_source("entry.is_file(follow_symlinks=False)")
        self.assertEqual("PARTIAL_UNSAFE", result["verdict"])


if __name__ == "__main__":
    unittest.main()
