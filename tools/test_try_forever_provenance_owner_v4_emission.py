#!/usr/bin/env python3
"""Regression source for TRY FOREVER provenance owner emission contract.

These fixtures pin the existing owner's composition of initial generated-index
artifact identity, late repository/artifact custody, portable report paths, and
final authority withholding. They are source until an authorized runner executes
them; importing this module is not test evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_generated_index_artifact_observation import (
    GeneratedIndexArtifactObservation,
)
from try_forever_repository_emission_observation import RepositoryEmissionObservation

HEAD = "1" * 40
OTHER_HEAD = "2" * 40
SHA_A = "a" * 64
SHA_B = "b" * 64


def stable_repository(*, head: str = HEAD) -> RepositoryEmissionObservation:
    return RepositoryEmissionObservation(
        status="OBSERVED",
        reason="fixture stable",
        head=head,
        dirty=False,
    )


def verified_index(path: Path, *, sha256: str = SHA_A) -> probe.IndexVerdict:
    return probe.IndexVerdict(
        status="VERIFIED_CURRENT",
        reason="fixture current",
        path=str(path),
        source_head=HEAD,
        generated_at="2026-08-19T15:00:00+00:00",
        dirty_source=False,
        age_hours=1.0,
        inspection_sha256=sha256,
    )


def stale_index(path: Path) -> probe.IndexVerdict:
    return probe.IndexVerdict(
        status="STALE",
        reason="fixture stale",
        path=str(path),
        source_head="0" * 40,
        generated_at="2026-08-18T15:00:00+00:00",
        dirty_source=False,
        age_hours=25.0,
        inspection_sha256="",
    )


class ProvenanceOwnerEmissionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.repo.mkdir(exist_ok=True)
        self.index_path = self.repo / "generated" / "skill-index.json"
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.skill = probe.SkillRecord(
            path="skills/example/SKILL.md",
            sha256="c" * 64,
            title="Example",
        )

    def tearDown(self):
        self.temp.cleanup()

    def run_main(
        self,
        *,
        index_verdict: probe.IndexVerdict,
        final_repository: RepositoryEmissionObservation | None = None,
        emission_sha256: str = SHA_A,
        strict: bool = False,
        generated_index_arg: Path | None = None,
    ) -> tuple[int, dict, mock.Mock]:
        generated_index = generated_index_arg or self.index_path
        argv = [
            "try_forever_skill_provenance_probe.py",
            "--repo-root",
            str(self.repo),
            "--generated-index",
            str(generated_index),
        ]
        if strict:
            argv.append("--strict")

        artifact_mock = mock.Mock(
            return_value=GeneratedIndexArtifactObservation(
                size_bytes=2,
                sha256=emission_sha256,
                utf8_text="{}",
            )
        )
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
            probe, "git_head", side_effect=[HEAD, HEAD]
        ), mock.patch.object(
            probe, "git_dirty", side_effect=[False, False]
        ), mock.patch.object(
            probe, "discover_skills", return_value=([self.skill], [])
        ), mock.patch.object(
            probe, "inspect_generated_index", return_value=index_verdict
        ), mock.patch.object(
            probe, "observe_generated_index_artifact", artifact_mock
        ), mock.patch.object(
            probe,
            "observe_repository_emission",
            return_value=final_repository or stable_repository(),
        ), redirect_stdout(stdout):
            code = probe.main()
        return code, json.loads(stdout.getvalue()), artifact_mock

    def test_initial_verified_index_retains_exact_whole_artifact_sha(self):
        payload = {
            "sourceHead": HEAD,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "dirtySource": False,
        }
        raw = json.dumps(payload).encode("utf-8")
        self.index_path.write_bytes(raw)

        verdict = probe.inspect_generated_index(
            self.index_path,
            current_head=HEAD,
            current_tree_dirty=False,
            max_age_hours=24.0,
            now=datetime.now(timezone.utc),
        )

        self.assertEqual("VERIFIED_CURRENT", verdict.status)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), verdict.inspection_sha256)

    def test_stable_repo_and_same_artifact_emit_current_schema_authority(self):
        code, report, artifact_mock = self.run_main(
            index_verdict=verified_index(self.index_path),
            emission_sha256=SHA_A,
        )

        self.assertEqual(0, code)
        self.assertEqual("try-forever-skill-provenance.v5", report["schema"])
        self.assertEqual(".", report["repositoryRoot"])
        self.assertEqual("REPOSITORY", report["repositoryRootScope"])
        self.assertTrue(report["skillAuthority"]["emissionAuthoritative"])
        self.assertEqual(1, report["skillCount"])
        self.assertEqual(["skills/example/SKILL.md"], [item["path"] for item in report["skills"]])
        self.assertEqual("VERIFIED_CURRENT", report["generatedIndex"]["status"])
        self.assertEqual(SHA_A, report["generatedIndex"]["inspectionSha256"])
        self.assertEqual(SHA_A, report["generatedIndex"]["emissionSha256"])
        self.assertEqual("STABLE", report["generatedIndex"]["emissionArtifactStatus"])
        self.assertFalse(report["generatedIndex"]["currentnessWithheld"])
        self.assertEqual("generated/skill-index.json", report["generatedIndex"]["path"])
        artifact_mock.assert_called_once()

    def test_changed_artifact_withholds_index_currentness_but_not_repository_skills(self):
        code, report, _artifact_mock = self.run_main(
            index_verdict=verified_index(self.index_path),
            emission_sha256=SHA_B,
        )

        self.assertEqual(0, code)
        self.assertTrue(report["skillAuthority"]["emissionAuthoritative"])
        self.assertEqual(1, report["skillCount"])
        self.assertEqual("UNRESOLVED", report["generatedIndex"]["status"])
        self.assertEqual("CHANGED", report["generatedIndex"]["emissionArtifactStatus"])
        self.assertTrue(report["generatedIndex"]["currentnessWithheld"])

    def test_late_repository_change_zeroes_skill_authority_and_index_currentness(self):
        code, report, _artifact_mock = self.run_main(
            index_verdict=verified_index(self.index_path),
            final_repository=stable_repository(head=OTHER_HEAD),
            emission_sha256=SHA_A,
        )

        self.assertEqual(0, code)
        self.assertFalse(report["skillAuthority"]["emissionAuthoritative"])
        self.assertEqual(0, report["skillCount"])
        self.assertEqual([], report["skills"])
        self.assertEqual(OTHER_HEAD, report["currentHead"])
        self.assertEqual("UNRESOLVED", report["generatedIndex"]["status"])
        self.assertTrue(report["generatedIndex"]["currentnessWithheld"])

    def test_strict_mode_fails_on_late_repository_custody_loss(self):
        code, report, _artifact_mock = self.run_main(
            index_verdict=verified_index(self.index_path),
            final_repository=stable_repository(head=OTHER_HEAD),
            strict=True,
        )

        self.assertEqual(2, code)
        self.assertFalse(report["skillAuthority"]["emissionAuthoritative"])

    def test_negative_prior_index_status_skips_needless_late_artifact_read(self):
        code, report, artifact_mock = self.run_main(
            index_verdict=stale_index(self.index_path),
        )

        self.assertEqual(0, code)
        self.assertEqual("STALE", report["generatedIndex"]["status"])
        self.assertEqual("UNRESOLVED", report["generatedIndex"]["emissionArtifactStatus"])
        artifact_mock.assert_not_called()

    def test_external_generated_index_path_is_not_leaked_into_report(self):
        external = self.repo.parent / "outside-secret-index.json"
        code, report, _artifact_mock = self.run_main(
            index_verdict=verified_index(external),
            generated_index_arg=external,
        )

        self.assertEqual(0, code)
        self.assertEqual("<external-path>", report["generatedIndex"]["path"])
        self.assertEqual("EXTERNAL", report["generatedIndex"]["pathScope"])
        self.assertNotIn(str(external), json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
