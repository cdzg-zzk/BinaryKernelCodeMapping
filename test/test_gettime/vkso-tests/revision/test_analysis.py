import unittest
from analyze import boot_values, summarize


def row(method, boot, repeat, value):
    return dict(variant="normal", role="read", scenario="monotonic", metric="cycles",
                unit="TSC cycles/call", protocol="test-fixture", method=method,
                boot_id=boot, round=str(repeat), value=str(value), image_sha256=boot)


class AnalysisTest(unittest.TestCase):
    def test_boots_not_rounds_determine_weight(self):
        rows = [row("raw", "a", i, 10) for i in range(100)]
        rows += [row("raw", "b", 0, 100), row("raw", "c", 0, 100)]
        rows += [row("vkso", str(i), 0, 110) for i in range(3)]
        result = summarize(rows, 100)[0]
        self.assertEqual(result["baseline_median"], 100)
        self.assertAlmostEqual(result["ratio"], 1.1)
        self.assertEqual(result["baseline_boots"], 3)

    def test_paired_boot_resampling_preserves_covariance(self):
        rows = [row(m, str(b), 0, value * scale)
                for b, value in enumerate([1, 10, 100, 1000, 10000])
                for m, scale in [("compact-split", 1), ("vkso", 2)]]
        result = summarize(rows, 100)[0]
        self.assertEqual(result["ci_low"], 2)
        self.assertEqual(result["ci_high"], 2)

    def test_duplicate_collection_is_rejected(self):
        r = row("raw", "a", 0, 10)
        with self.assertRaises(ValueError):
            boot_values([r, r])

    def test_single_boot_cannot_create_confidence_interval(self):
        result = summarize([row("raw", "a", 0, 1), row("vkso", "b", 0, 2)], 100)[0]
        self.assertEqual(result["ci_low"], "")

    def test_zero_metric_retains_absolute_difference_interval(self):
        rows = [row(m, str(b), 0, v) for b in range(5)
                for m, v in [('compact-split', 0), ('vkso', 2)]]
        result = summarize(rows, 100)[0]
        self.assertEqual(result['ratio'], '')
        self.assertEqual(result['difference_ci_low'], 2)
        self.assertEqual(result['difference_ci_high'], 2)

    def test_incomplete_paired_boots_are_rejected(self):
        rows = [row("compact-split", "a", 0, 1), row("compact-split", "b", 0, 1),
                row("vkso", "a", 0, 2)]
        with self.assertRaises(ValueError):
            summarize(rows, 100)


if __name__ == "__main__":
    unittest.main()
