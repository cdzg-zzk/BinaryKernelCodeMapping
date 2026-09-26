#!/usr/bin/env python3
"""Offline statistical identities, not target-kernel or performance tests."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from distributions import band_stats, decompose, delta_summary


class DistributionTests(unittest.TestCase):
    def test_paired_boot_interval_preserves_common_drift(self):
        s=delta_summary([10,100,1000,10000],[12,102,1002,10002])
        self.assertEqual(s['delta'],2)
        self.assertEqual(s['delta_bootstrap95'],[2,2])

    def test_mixture_only_and_location_only(self):
        mix=decompose([100]*3+[150],[100]+[150]*3,120,120)
        self.assertEqual(mix['location'],0)
        self.assertEqual(mix['mixture'],25)
        loc=decompose([100,150],[105,155],120,120)
        self.assertEqual(loc['mixture'],0)
        self.assertEqual(loc['location'],5)

    def test_tail_is_retained_unless_explicit_sensitivity(self):
        r,v=[100,150],[100,15000]
        full=decompose(r,v,120,120)
        capped=decompose(r,v,120,120,300)
        self.assertEqual(full['delta'],7425)
        self.assertEqual(capped['delta'],75)
        self.assertEqual(full['location']+full['mixture'],full['delta'])

    def test_missing_band_refused_not_fabricated(self):
        with self.assertRaises(ValueError):band_stats([90,100],120)

    def test_backend_thresholds_remain_explicit(self):
        s=decompose([100,130],[105,115],120,110)
        self.assertEqual(s['raw']['high_fraction'],.5)
        self.assertEqual(s['vkso']['high_fraction'],.5)
        self.assertEqual(s['delta'],-5)


if __name__=='__main__':unittest.main()
