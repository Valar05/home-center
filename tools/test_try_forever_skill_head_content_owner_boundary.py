#!/usr/bin/env python3
"""RED owner-boundary regression for exact repository-skill content↔HEAD binding.

Supporting HEAD-tree and Git-blob identity organs exist, but the sole provenance
owner does not consume them yet. This fixture is intentionally RED until one
reviewed owner composition uses those existing organs without adding a second
content read or second provenance owner.
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
        self.assertIn("git_blob", self.content_custody)
        self.assertNotIn("git hash-object", self.content_custody)

    def test_owner_composes_existing_head_blob_observation(self):
        self.assertIn("try_forever_skill_head_blob_observation", self.owner)
        self.assertIn("observe_head_skill_blobs", self.owner)

    def test_owner_composes_existing_content_binding_policy(self):
        self.assertIn("try_forever_skill_head_content_binding", self.owner)
        self.assertIn("assess_skill_head_content_binding", self.owner)

    def test_owner_does_not_claim_status_or_tracked_membership_overrides_mismatch(self):
        self.assertIn("HeadSkillContentMismatch", self.owner)
        self.assertIn("content", self.owner)
        self.assertIn("HEAD", self.owner)


if __name__ == "__main__":
    unittest.main()
