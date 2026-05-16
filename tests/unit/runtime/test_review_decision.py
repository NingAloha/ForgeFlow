from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.approval_queue import materialize_pending_reviews
from forgeflow.runtime.review_decision import write_review_decision
from forgeflow.runtime.review_state import load_review_state, upsert_pending_review


class RuntimeReviewDecisionTests(unittest.TestCase):
    def test_write_review_decision_updates_review_state_and_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260101T000000Z-demo0000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            upsert_pending_review(run_dir=run_dir, run_id=run_id, artifact="spec")
            pending_before = materialize_pending_reviews(runs_root)
            self.assertEqual(len(pending_before), 1)

            _ = write_review_decision(
                runs_root=runs_root,
                run_id=run_id,
                artifact="spec",
                review_status="approved",
                reviewed_by="alice",
                review_reason="looks good",
            )

            state = load_review_state(run_dir)
            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(state.items[0].review_status, "approved")
            self.assertEqual(state.items[0].reviewed_by, "alice")

            pending_after = materialize_pending_reviews(runs_root)
            self.assertEqual(pending_after, [])


if __name__ == "__main__":
    unittest.main()

