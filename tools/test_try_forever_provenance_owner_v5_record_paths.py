#!/usr/bin/env python3
"""Owner-integration regression source for provenance schema v5 record paths.

This fixture is intentionally RED SOURCE until the existing
``try_forever_skill_provenance_probe`` consumes the already-reviewed
repository-relative report-path projection at serialization time. It owns no
filesystem authority, renderer, scheduler, phone surface, or P0 lane.

SOURCE / REGRESSION_SOURCE only. Importing or committing this file is not test
execution evidence.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_repository_emission_observation import RepositoryEmissionObservation

HEAD = "1" * 40


def stable_repository() -> RepositoryEmissionObservation:
    return RepositoryEmissionObservation(
        status="OBSERVED",
        reason="fixture stable",
        head=HEAD,
        dirty=False,
    )


class ProvenanceOwnerV5RecordPathsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.skill_path = "skills/line\nbidi\u202ejoin\u200d/SKILL.md"
        self.error_path = "skills/error\nbidi\u202e/SKILL.md"
        self.related_path = r"skills/literal\u{202E}/SKILL.md"
        self.skill = probe.SkillRecord(
            path=self.skill_path,
            sha256="c" * 64,
            title="Example",
        )
        self.error = probe.DiscoveryError(
            path=self.error_path,
            stage="identity",
            error_type="FixtureError",
            reason="fixture diagnostic",
            related_path=self.related_path,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_main(self) -> tuple[int, dict]:
        argv = [
            "try_forever_skill_provenance_probe.py",
            "--repo-root",
            str(self.repo),
        ]
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
            probe, "git_head", side_effect=[HEAD, HEAD]
        ), mock.patch.object(
            probe, "git_dirty", side_effect=[False, False]
        ), mock.patch.object(
            probe, "discover_skills", return_value=([self.skill], [self.error])
        ), mock.patch.object(
            probe, "observe_repository_emission", return_value=stable_repository()
        ), redirect_stdout(stdout):
            code = probe.main()
        return code, json.loads(stdout.getvalue())

    def test_owner_serializes_every_repository_record_path_through_v5_display_projection(self) -> None:
        code, report = self.run_main()

        self.assertEqual(0, code)
        self.assertEqual("try-forever-skill-provenance.v5", report["schema"])

        emitted_skill = report["skills"][0]["path"]
        self.assertNotIn("\n", emitted_skill)
        self.assertNotIn("\u202e", emitted_skill)
        self.assertNotIn("\u200d", emitted_skill)
        self.assertIn(r"\u{000A}", emitted_skill)
        self.assertIn(r"\u{202E}", emitted_skill)
        self.assertIn(r"\u{200D}", emitted_skill)

        emitted_error = report["discoveryErrors"][0]
        self.assertNotIn("\n", emitted_error["path"])
        self.assertNotIn("\u202e", emitted_error["path"])
        self.assertIn(r"\u{000A}", emitted_error["path"])
        self.assertIn(r"\u{202E}", emitted_error["path"])
        self.assertIn(r"\\u{202E}", emitted_error["related_path"])

        # Display projection must not mutate the authority/diagnostic identities
        # retained by the owner before serialization.
        self.assertEqual("skills/line\nbidi\u202ejoin\u200d/SKILL.md", self.skill.path)
        self.assertEqual("skills/error\nbidi\u202e/SKILL.md", self.error.path)
        self.assertEqual(r"skills/literal\u{202E}/SKILL.md", self.error.related_path)

    def test_literal_marker_spelling_cannot_collide_with_actual_bidi_control(self) -> None:
        actual = probe.SkillRecord(
            path="skills/x\u202ey/SKILL.md",
            sha256="d" * 64,
            title="Actual",
        )
        literal = probe.DiscoveryError(
            path=r"skills/x\u{202E}y/SKILL.md",
            stage="identity",
            error_type="FixtureError",
            reason="literal marker",
        )
        stdout = io.StringIO()
        argv = ["try_forever_skill_provenance_probe.py", "--repo-root", str(self.repo)]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
            probe, "git_head", side_effect=[HEAD, HEAD]
        ), mock.patch.object(
            probe, "git_dirty", side_effect=[False, False]
        ), mock.patch.object(
            probe, "discover_skills", return_value=([actual], [literal])
        ), mock.patch.object(
            probe, "observe_repository_emission", return_value=stable_repository()
        ), redirect_stdout(stdout):
            probe.main()
        report = json.loads(stdout.getvalue())
        self.assertNotEqual(
            report["skills"][0]["path"],
            report["discoveryErrors"][0]["path"],
        )
        self.assertIn(r"\u{202E}", report["skills"][0]["path"])
        self.assertIn(r"\\u{202E}", report["discoveryErrors"][0]["path"])


if __name__ == "__main__":
    unittest.main()
