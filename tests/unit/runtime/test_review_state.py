from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.approval_queue import materialize_pending_reviews
from forgeflow.runtime.review_state import load_review_state, upsert_pending_review


class RuntimeReviewStateTests(unittest.TestCase):
    def test_upsert_pending_review_writes_review_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "20260101T000000Z-demo0000"
            run_dir.mkdir(parents=True, exist_ok=True)
            upsert_pending_review(
                run_dir=run_dir,
                run_id="20260101T000000Z-demo0000",
                artifact="spec",
            )
            state = load_review_state(run_dir)
            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(state.run_id, "20260101T000000Z-demo0000")
            self.assertEqual(len(state.items), 1)
            self.assertEqual(state.items[0].artifact, "spec")
            self.assertEqual(state.items[0].review_status, "pending")

    def test_materialize_pending_reviews_scans_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            run_dir = runs_root / "20260101T000000Z-demo0000"
            run_dir.mkdir(parents=True, exist_ok=True)
            upsert_pending_review(
                run_dir=run_dir,
                run_id="20260101T000000Z-demo0000",
                artifact="solution",
            )
            pending = materialize_pending_reviews(runs_root)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].run_id, "20260101T000000Z-demo0000")
            self.assertEqual(pending[0].artifact, "solution")


if __name__ == "__main__":
    unittest.main()

