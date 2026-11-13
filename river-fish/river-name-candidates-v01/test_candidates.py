#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("candidate_validator", HERE / "validate_candidates.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


class RiverNameCandidateLayerTests(unittest.TestCase):
    def test_reviewed_candidates_remain_outside_fixed_coverage(self):
        result = VALIDATOR.validate()
        self.assertEqual(result["fixed_coverage_denominator"], 1127)
        self.assertEqual(result["connected_groups_at_baseline"], 477)
        self.assertEqual(result["candidate_count"], 58)
        self.assertEqual(result["candidate_rows_with_cross_context_exact_name_matches"], 6)
        self.assertEqual(result["candidate_rows_added_to_fixed_denominator"], 0)
        self.assertEqual(result["candidate_rows_published"], 0)
        self.assertEqual(result["candidate_fish_connections"], 0)


if __name__ == "__main__":
    unittest.main()
