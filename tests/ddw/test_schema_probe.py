"""Guard comparison semantics, integrity and scope; no inference or network."""
# ruff: noqa: PT009, PT027

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phd_searcher.ddw import schema_probe as p
from phd_searcher.ddw.worker import encoded

ROOT = Path(__file__).parent / "snapshots"


class SchemaProbeTests(unittest.TestCase):
    def test_full_cohort_existing_routes(self):
        bundle = p.read_bundle(ROOT / "manifest.json")
        states = [p.offline_probe(case)["decision"] for case in bundle["cases"]]
        self.assertEqual(len(states), 16)
        self.assertEqual(states.count("reused"), 8)
        self.assertEqual(states.count("adapter"), 3)
        self.assertEqual(states.count("deferred"), 2)
        self.assertEqual(states.count("generation_candidate"), 3)

    def test_replay_does_not_revalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            receipt = p.execute(ROOT / "manifest.json", output)
            with patch.object(p, "offline_probe", side_effect=AssertionError("replay")):
                self.assertEqual(p.execute(ROOT / "manifest.json", output), receipt)
            receipt["results"][0]["decision"] = "forged"
            output.write_bytes(encoded(receipt))
            with self.assertRaisesRegex(ValueError, "corruption"):
                p.execute(ROOT / "manifest.json", output)

    def test_scope_is_not_widened_for_more_reuse(self):
        case = p.read_bundle(ROOT / "manifest.json")["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / case["snapshot"]).write_text(case.pop("html"))
            case["candidates"][0]["source_url"] = "https://other.example/jobs"
            manifest = target / "manifest.json"
            manifest.write_text(json.dumps({"version": 1, "operation": "schema-probe", "cases": [case]}))
            with self.assertRaisesRegex(ValueError, "cache_scope"):
                p.read_bundle(manifest)

    def test_bad_snapshot_hash_rejected(self):
        bundle = json.loads((ROOT / "manifest.json").read_bytes())
        bundle["cases"][0]["snapshot_sha256"] = "bad"
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            bundle["cases"] = bundle["cases"][:1]
            case = bundle["cases"][0]
            (manifest.parent / case["snapshot"]).write_bytes((ROOT / case["snapshot"]).read_bytes())
            manifest.write_text(json.dumps(bundle))
            with self.assertRaisesRegex(ValueError, "snapshot_hash"):
                p.read_bundle(manifest)

    def test_structural_success_is_not_opportunity_correctness(self):
        bundle = p.read_bundle(ROOT / "manifest.json")
        case = next(c for c in bundle["cases"] if c["id"] == "iow-phd")
        result = p.offline_probe(case)
        self.assertEqual(result["decision"], "reused")
        self.assertEqual(result["items"][0]["title"], "Pursuing a PhD at IOW")
        self.assertEqual(json.loads((ROOT / "audit.json").read_bytes())["iow-phd"]["expected_pairs"], [])

    def test_rendered_and_static_inputs_are_not_equivalent(self):
        bundle = p.read_bundle(ROOT / "manifest.json")
        static = next(c for c in bundle["cases"] if c["id"] == "champ-static")
        rendered = next(c for c in bundle["cases"] if c["id"] == "champ-rendered")
        self.assertNotEqual(static["snapshot_sha256"], rendered["snapshot_sha256"])
        self.assertEqual(p.offline_probe(static)["decision"], "generation_candidate")
        self.assertEqual(p.offline_probe(rendered)["decision"], "reused")

    def test_full_validator_preserves_strict_fields(self):
        case = copy.deepcopy(p.read_bundle(ROOT / "manifest.json")["cases"][0])
        case["expected_fields"] = ["title", "nonexistent_required_field"]
        self.assertEqual(p.offline_probe(case)["decision"], "generation_candidate")
