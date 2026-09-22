#!/usr/bin/env python3

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("summarize.py")


class SummarizeTests(unittest.TestCase):
    def test_statistics_use_lossless_counters_not_display_column(self) -> None:
        fields = (
            "backend", "case", "outer_run", "bytes", "compressed_bytes",
            "repeats", "elapsed_ns", "mean_ms", "throughput_mib_s",
        )
        rows = [
            ("native", "sample", 0, 1048576, 1, 1, 1000000000, 1000, 999),
            ("kernel-vkso", "sample", 0, 1048576, 1, 1, 2000000000, 2000, 999),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.csv"
            aggregate = root / "aggregate.csv"
            summary = root / "summary.md"
            with raw.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerows(rows)
            subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--input", str(raw),
                    "--aggregate", str(aggregate),
                    "--summary", str(summary),
                ],
                check=True,
            )
            with aggregate.open(newline="") as stream:
                aggregate_rows = list(csv.DictReader(stream))
            summary_text = summary.read_text()

        by_backend = {row["backend"]: row for row in aggregate_rows}
        self.assertEqual(by_backend["native"]["median_mib_s"], "1.000")
        self.assertEqual(
            by_backend["kernel-vkso"]["median_mib_s"], "0.500"
        )
        self.assertIn("0.500×", summary_text)


if __name__ == "__main__":
    unittest.main()
