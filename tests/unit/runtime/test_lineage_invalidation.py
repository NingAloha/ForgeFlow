from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.lineage import invalidated_artifacts, load_lineage, upsert_lineage_entry


class RuntimeLineageInvalidationTests(unittest.TestCase):
    def test_upstream_regeneration_invalidates_downstream_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "20260101T000000Z-demo0000"
            run_dir.mkdir(parents=True, exist_ok=True)
            run_id = "20260101T000000Z-demo0000"

            # Build full chain once.
            upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact="spec", generated_by="R")
            upsert_lineage_entry(
                run_dir=run_dir, run_id=run_id, artifact="solution", generated_by="S"
            )
            upsert_lineage_entry(
                run_dir=run_dir, run_id=run_id, artifact="system_design", generated_by="D"
            )
            upsert_lineage_entry(
                run_dir=run_dir,
                run_id=run_id,
                artifact="implementation_status",
                generated_by="I",
            )
            upsert_lineage_entry(
                run_dir=run_dir, run_id=run_id, artifact="test_report", generated_by="T"
            )

            # Regenerate spec: should mark downstream as invalidated_by=["spec"].
            upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact="spec", generated_by="R2")
            lineage = load_lineage(run_dir)
            self.assertIsNotNone(lineage)
            assert lineage is not None
            by_artifact = {e.artifact: e for e in lineage.entries}
            self.assertEqual(by_artifact["spec"].invalidated_by, [])
            self.assertEqual(by_artifact["solution"].invalidated_by, ["spec"])
            self.assertEqual(by_artifact["system_design"].invalidated_by, ["spec"])
            self.assertEqual(by_artifact["implementation_status"].invalidated_by, ["spec"])
            self.assertEqual(by_artifact["test_report"].invalidated_by, ["spec"])

            self.assertEqual(
                invalidated_artifacts(lineage),
                [
                    "implementation_status",
                    "solution",
                    "system_design",
                    "test_report",
                ],
            )


if __name__ == "__main__":
    unittest.main()

