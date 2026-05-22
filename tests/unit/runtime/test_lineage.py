from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.lineage import (
    depends_on_for_artifact,
    load_lineage,
    upsert_lineage_entry,
)


class RuntimeLineageTests(unittest.TestCase):
    def test_depends_on_chain(self) -> None:
        self.assertEqual(depends_on_for_artifact("spec"), [])
        self.assertEqual(depends_on_for_artifact("solution"), ["spec"])
        self.assertEqual(depends_on_for_artifact("system_design"), ["solution"])
        self.assertEqual(depends_on_for_artifact("implementation_status"), ["system_design"])
        self.assertEqual(depends_on_for_artifact("test_report"), ["implementation_status"])

        deps = depends_on_for_artifact("solution")
        deps.append("x")
        self.assertEqual(depends_on_for_artifact("solution"), ["spec"])

    def test_upsert_writes_atomic_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "20260101T000000Z-demo0000"
            run_dir.mkdir(parents=True, exist_ok=True)
            upsert_lineage_entry(
                run_dir=run_dir,
                run_id="20260101T000000Z-demo0000",
                artifact="spec",
                generated_by="RequirementsEngineerAgent",
            )
            lineage_path = run_dir / "lineage.json"
            self.assertTrue(lineage_path.exists())
            payload = json.loads(lineage_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema_version"), "1")
            self.assertEqual(payload.get("run_id"), "20260101T000000Z-demo0000")

            loaded = load_lineage(run_dir)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(len(loaded.entries), 1)
            self.assertEqual(loaded.entries[0].artifact, "spec")
            self.assertEqual(loaded.entries[0].depends_on, [])
            self.assertEqual(loaded.entries[0].generated_by, "RequirementsEngineerAgent")

    def test_load_lineage_returns_none_on_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "20260101T000000Z-demo0000"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "lineage.json").write_text("{bad json", encoding="utf-8")
            self.assertIsNone(load_lineage(run_dir))


if __name__ == "__main__":
    unittest.main()
