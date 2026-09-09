#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import judgment_jar_task_router as router
from judgment_jar_common import CABINET_ORIGIN, DISCOVERY_ORIGIN, RegistryError


REGISTRY_ID = "1UixBuLJRw-x5BoMGx81YXRpuN66iZhGGJoz40Iqx48Q"
PASTA_ID = "1VlPlNiiRBW5KSI9Bb3zryWTDRkNRahfQkvlFV7er_KE"
ARCHIVE_ID = "1JQ3Fkt-6UiS5HIc8PFO0y41mmeENB26O14-BeCewrMM"
PASTA_JAR_ID = "pasta-fahr-the-noodle-remembers"

registry_text = f"""JUDGMENT JAR REGISTRY
Pasta’Fahr aliases for retrieval only: Pasta'Fahr; Pasta Fahr; Pasta'far; Pasta’far; “pasta apostrophe fahr”; “pasta apostrophe far”. Canonical Jar ID: {PASTA_ID}. These aliases do not create separate Characters or Jars.
"""
canonical = {
    "id": PASTA_JAR_ID,
    "title": "Pasta’Fahr — The Noodle Remembers",
    "origin": CABINET_ORIGIN,
    "sourceFileId": PASTA_ID,
    "sourceType": "spreadsheet",
    "aliases": ["pasta-fahr-the-noodle-remembers"],
}
archive = {
    "id": "archive-copy-do-not-resolve-pasta-fahr",
    "title": "ARCHIVE COPY — DO NOT RESOLVE — Pasta’Fahr — Judgment Jar — 1JQ3F",
    "origin": DISCOVERY_ORIGIN,
    "sourceFileId": ARCHIVE_ID,
    "sourceType": "spreadsheet",
    "aliases": ["pasta-fahr"],
}
registry = {
    "homeCenter": {
        "state": "synced",
        "complete": True,
        "registryFileId": REGISTRY_ID,
        "registryTextSha256": "registry-sha",
        "registryText": registry_text,
    },
    "jars": [canonical, archive],
}

resolved = router.resolve_task_jars(registry, "Pasta apostrophe far. What does he actually judge?")
assert [item["sourceFileId"] for item in resolved] == [PASTA_ID]
assert router.resolve_task_jars(registry, "What do you think of Pastafarian?") == []
assert router.resolve_task_jars(registry, "Pasta'Fahr, report.")[0]["sourceFileId"] == PASTA_ID
assert router.has_explicit_jar_signal("Call the judgment jar") is True

with tempfile.TemporaryDirectory(prefix="jar-task-router-") as temp:
    config_path = Path(temp) / "judgment-jars.json"
    config_path.write_text(json.dumps({
        "schema": "home-center.judgment-jars.config.v1",
        "repositorySourcePattern": ".continue/rules/*judgement-jar*.md",
        "homeCenter": {"registryFileId": REGISTRY_ID},
        "runtime": {},
    }), encoding="utf-8")

    original_ensure = router.ensure_registry
    original_fetch = router.fetch_native_source
    try:
        router.ensure_registry = lambda *args, **kwargs: (registry, {})
        router.fetch_native_source = lambda *args, **kwargs: {
            "state": "synced",
            "sourceSha256": "canonical-pasta-source-sha",
            "sheet": {
                "Judgment": "Which strands are living lineage—and which are accidental captivity?",
                "Compact law": "Trace the noodle. Name the sauce. Keep what feeds. Cut what only clings.",
            },
        }
        packet = router.task_source_packet(
            "Pasta apostrophe far. What does he actually judge?",
            root=Path(temp),
            cache=Path(temp) / "cache.json",
            config_path=config_path,
        )
        assert f"REGISTRY_FILE_ID: {REGISTRY_ID}" in packet
        assert f"SOURCE_FILE_ID: {PASTA_ID}" in packet
        assert "Which strands are living lineage" in packet
        assert "Trace the noodle" in packet
        assert ARCHIVE_ID not in packet
        assert "Pastafarian" not in packet

        router.fetch_native_source = lambda *args, **kwargs: {
            "state": "stale",
            "sourceSha256": "old",
            "sheet": {"Judgment": "old"},
        }
        try:
            router.task_source_packet(
                "Pasta apostrophe far",
                root=Path(temp),
                cache=Path(temp) / "cache.json",
                config_path=config_path,
            )
            raise AssertionError("stale native source must fail closed")
        except RegistryError as exc:
            assert "JAR_UNRESOLVED" in str(exc)

        try:
            router.task_source_packet(
                "Call the Mystery Judgment Jar",
                root=Path(temp),
                cache=Path(temp) / "cache.json",
                config_path=config_path,
            )
            raise AssertionError("unknown explicit Jar request must fail closed")
        except RegistryError as exc:
            assert "JAR_UNRESOLVED" in str(exc)
    finally:
        router.ensure_registry = original_ensure
        router.fetch_native_source = original_fetch

launcher = (Path(__file__).resolve().parent / "adam_receipted_worker.py").read_text(encoding="utf-8")
runtime = (Path(__file__).resolve().parent / "judgment_jar_runtime.py").read_text(encoding="utf-8")
assert "task_source_packet(task" in launcher
assert "_task_context = task" in launcher
assert "runtime_active_jars(_task_context, limit)" in launcher
assert "task_source_packet(str(task)" in runtime
assert "JAR_UNRESOLVED" in runtime

print(json.dumps({
    "ok": True,
    "schema": "judgment-jar-task-router-contract.v1",
    "canonicalRegistryFileId": REGISTRY_ID,
    "canonicalPastaFahrFileId": PASTA_ID,
    "voiceAlias": "pasta apostrophe far",
    "pastafarianDoesNotResolve": True,
    "archiveDoesNotResolve": True,
    "staleNativeSourceFailsClosed": True,
    "unknownExplicitJarFailsClosed": True,
    "planningAndExecutionWired": True,
}, sort_keys=True))
