from __future__ import annotations

import unittest

from forgeflow.runtime.needs_rerun import compute_needs_rerun


class NeedsRerunTests(unittest.TestCase):
    def test_needs_rerun_maps_artifacts_to_stages(self) -> None:
        result = compute_needs_rerun(
            invalidated_artifacts=["solution"],
            pending_review_artifacts=["spec"],
            rejected_review_artifacts=["system_design"],
        )
        self.assertEqual(sorted(result.artifacts), ["solution", "spec", "system_design"])
        # REQUIREMENTS should appear because spec is pending; order is insertion order in compute.
        self.assertIn("REQUIREMENTS", result.stages)
        self.assertIn("SOLUTION", result.stages)
        self.assertIn("DESIGN", result.stages)


if __name__ == "__main__":
    unittest.main()

