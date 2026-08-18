#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_identity_set import (
    casefold_skill_identity,
    find_case_insensitive_collisions,
    has_ambiguous_skill_identity,
)


class SkillIdentitySetTest(unittest.TestCase):
    def test_distinct_owner_keys_are_unambiguous(self):
        paths = [
            "skills/alpha/SKILL.md",
            "skills/beta/SKILL.md",
        ]
        self.assertEqual((), find_case_insensitive_collisions(paths))
        self.assertFalse(has_ambiguous_skill_identity(paths))

    def test_case_only_aliases_form_one_collision_without_a_winner(self):
        paths = [
            "skills/alpha/SKILL.md",
            "skills/ALPHA/SKILL.md",
        ]
        collisions = find_case_insensitive_collisions(paths)
        self.assertEqual(1, len(collisions))
        self.assertEqual(
            casefold_skill_identity("skills/alpha/SKILL.md"),
            collisions[0].canonical_id,
        )
        self.assertEqual(tuple(sorted(paths)), collisions[0].paths)
        self.assertTrue(has_ambiguous_skill_identity(paths))

    def test_input_order_cannot_choose_the_authoritative_alias(self):
        forward = ["skills/a/SKILL.md", "skills/A/SKILL.md"]
        reverse = list(reversed(forward))
        self.assertEqual(
            find_case_insensitive_collisions(forward),
            find_case_insensitive_collisions(reverse),
        )

    def test_exact_duplicate_input_is_not_a_second_repository_identity(self):
        path = "skills/alpha/SKILL.md"
        self.assertEqual((), find_case_insensitive_collisions([path, path]))

    def test_empty_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            casefold_skill_identity("")


if __name__ == "__main__":
    unittest.main()
