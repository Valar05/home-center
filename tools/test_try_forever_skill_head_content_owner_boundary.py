#!/usr/bin/env python3
"""RED owner-boundary regression for exact repository-skill content↔HEAD binding.

The single-artifact content observation now exposes Git blob identity derived from
that same admitted artifact, and bounded raw-HEAD blob observation/binding organs
already exist. The sole provenance owner still does not compose them. This fixture
stays intentionally RED until reviewed owner wiring uses those existing organs
without a second content read, per-file Git query, or second provenance owner.
"""

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class SkillHeadContentOwnerBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.owner = (TOOLS_DIR / "try_forever_skill_provenance_probe.py").read_text(
            encoding="utf-8"
        )
        cls.content_custody = (TOOLS_DIR / "try_forever_skill_content_custody.py").read_text(
            encoding="utf-8"
        )

    def test_single_artifact_content_observation_exposes_git_blob_identity(self):
        self.assertIn("git_blob_identity", self.content_custody)
        self.assertIn("git_blob_content_identity_from_utf8", self.content_custody)
        self.assertNotIn("git hash-object", self.content_custody)

    def test_owner_composes_existing_head_blob_observation(self):
        self.assertIn("try_forever_skill_head_blob_observation", self.owner)
        self.assertIn("observe_head_skill_blobs", self.owner)

    def test_owner_observes_bounded_head_blob_set_once_before_per_file_loop(self):
        self.assertEqual(self.owner.count("observe_head_skill_blobs("), 1)
        observation_index = self.owner.index("observe_head_skill_blobs(")
        loop_index = self.owner.index("for path in candidates:")
        self.assertLess(observation_index, loop_index)

    def test_owner_composes_existing_content_binding_policy(self):
        self.assertIn("try_forever_skill_head_content_binding", self.owner)
        self.assertIn("assess_skill_head_content_binding", self.owner)
        self.assertIn("content.git_blob_identity", self.owner)

    def test_owner_does_not_recompute_git_blob_identity_from_another_read(self):
        self.assertNotIn("git_blob_content_identity_from_utf8", self.owner)
        self.assertNotIn("git_blob_content_identity(", self.owner)
        self.assertNotIn("git hash-object", self.owner)

    def test_owner_binds_against_certified_discovery_head(self):
        self.assertIn("authority_head", self.owner)
        self.assertIn("snapshot_before.head", self.owner)
        call_index = self.owner.index("discover_skills(", self.owner.index("def main"))
        snapshot_index = self.owner.index("snapshot_before = observe_repository_emission")
        self.assertLess(snapshot_index, call_index)

    def test_owner_rejects_missing_or_mismatched_head_content_before_record_append(self):
        self.assertIn("HeadSkillContentMismatch", self.owner)
        self.assertIn("HeadSkillContentUnavailable", self.owner)
        binding_index = self.owner.index("assess_skill_head_content_binding")
        append_index = self.owner.index("records.append(SkillRecord")
        self.assertLess(binding_index, append_index)

    def test_owner_keeps_single_provenance_owner(self):
        self.assertNotIn("class SecondaryProvenance", self.owner)
        self.assertNotIn("def discover_head_authoritative_skills", self.owner)


if __name__ == "__main__":
    unittest.main()
