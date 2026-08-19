#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import try_forever_skill_provenance_probe as probe


class ProvenanceReportOwnerIntegrationTest(unittest.TestCase):
    def _run_owner(self, *, final_head: str = "abc123") -> tuple[int, dict]:
        record = probe.SkillRecord(
            path="skills/example/SKILL.md",
            sha256="a" * 64,
            title="Example",
        )
        index = probe.IndexVerdict(
            status="VERIFIED_CURRENT",
            reason="fixture",
            path="/home/alice/generated-index.json",
            source_head="abc123",
            generated_at="2026-08-18T22:00:00+00:00",
            dirty_source=False,
            age_hours=0.0,
        )
        stdout = io.StringIO()
        argv = [
            "try_forever_skill_provenance_probe.py",
            "--repo-root",
            "/srv/home-center",
            "--generated-index",
            "/home/alice/generated-index.json",
            "--expected-head",
            "abc123",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(probe, "git_head", side_effect=["abc123", "abc123", final_head]),
            patch.object(probe, "git_dirty", side_effect=[False, False, False]),
            patch.object(probe, "discover_skills", return_value=([record], [])),
            patch.object(probe, "inspect_generated_index", return_value=index),
            redirect_stdout(stdout),
        ):
            status = probe.main()
        return status, json.loads(stdout.getvalue())

    def test_owner_projects_report_paths_without_leaking_host_topology(self) -> None:
        status, report = self._run_owner()
        self.assertEqual(0, status)
        self.assertEqual("try-forever-skill-provenance.v4", report["schema"])
        self.assertEqual(".", report["repositoryRoot"])
        self.assertEqual("REPOSITORY", report["repositoryRootScope"])
        self.assertEqual("<external-path>", report["generatedIndex"]["path"])
        self.assertEqual("EXTERNAL", report["generatedIndex"]["pathScope"])
        self.assertNotIn("alice", json.dumps(report, sort_keys=True))
        self.assertTrue(report["skillAuthority"]["authoritative"])
        self.assertEqual(1, report["skillCount"])

    def test_late_head_change_withholds_previously_certified_skill_authority(self) -> None:
        status, report = self._run_owner(final_head="def456")
        self.assertEqual(0, status)
        self.assertEqual("UNSTABLE", report["reportEmissionSnapshot"]["status"])
        self.assertEqual("EMISSION_SNAPSHOT_UNSTABLE", report["skillAuthority"]["status"])
        self.assertFalse(report["skillAuthority"]["authoritative"])
        self.assertEqual(0, report["skillCount"])
        self.assertEqual([], report["skills"])

    def test_strict_mode_treats_late_emission_instability_as_failure(self) -> None:
        record = probe.SkillRecord(
            path="skills/example/SKILL.md",
            sha256="a" * 64,
            title="Example",
        )
        index = probe.IndexVerdict(
            status="UNRESOLVED",
            reason="no generated index supplied",
            path="",
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
        stdout = io.StringIO()
        argv = [
            "try_forever_skill_provenance_probe.py",
            "--repo-root",
            "/srv/home-center",
            "--expected-head",
            "abc123",
            "--strict",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(probe, "git_head", side_effect=["abc123", "abc123", "def456"]),
            patch.object(probe, "git_dirty", side_effect=[False, False, False]),
            patch.object(probe, "discover_skills", return_value=([record], [])),
            patch.object(probe, "inspect_generated_index", return_value=index),
            redirect_stdout(stdout),
        ):
            status = probe.main()
        report = json.loads(stdout.getvalue())
        self.assertEqual(2, status)
        self.assertFalse(report["skillAuthority"]["authoritative"])
        self.assertEqual([], report["skills"])


if __name__ == "__main__":
    unittest.main()
