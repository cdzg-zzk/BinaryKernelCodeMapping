"""Check boot-level uncertainty against an independent weighted-count oracle."""
from collections import Counter
import itertools
import math
from pathlib import Path
import statistics as st
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from read_evaluation import exact_intervals
from results import percentile


def weighted_boot_medians(values):
    distribution=Counter()
    for counts in itertools.product(range(5),repeat=4):
        if sum(counts)!=4:continue
        expanded=[v for n,v in zip(counts,values) for _ in range(n)]
        weight=math.factorial(4)//math.prod(math.factorial(n) for n in counts)
        distribution[st.median(expanded)]+=weight
    assert sum(distribution.values())==256
    return distribution


class BootIntervals(unittest.TestCase):
    def test_constant_boots_do_not_gain_fake_inner_replication(self):
        x=exact_intervals([10]*4,[12]*4)
        for key in ['delta_ci95_low','delta_ci95_high','block_ci95_low','block_ci95_high']:
            self.assertEqual(x[key],2.)
        self.assertEqual(x['ratio_ci95_low'],1.2)
        self.assertEqual(x['ratio_ci95_high'],1.2)

    def test_exact_interval_matches_multinomial_oracle(self):
        r=[10.,11.,13.,21.];v=[9.,12.,14.,17.]
        rr,vv=weighted_boot_medians(r),weighted_boot_medians(v)
        d=[b-a for a,wa in rr.items() for b,wb in vv.items() for _ in range(wa*wb)]
        q=[b/a for a,wa in rr.items() for b,wb in vv.items() for _ in range(wa*wb)]
        got=exact_intervals(r,v)
        for xs,prefix in [(d,'delta'),(q,'ratio')]:
            for prob,suffix in [(.025,'low'),(.975,'high')]:
                self.assertAlmostEqual(got[f'{prefix}_ci95_{suffix}'],percentile(xs,prob),places=12)
        permuted=exact_intervals(r,list(reversed(v)))
        self.assertEqual(got['delta_ci95_low'],permuted['delta_ci95_low'])
        self.assertEqual(got['delta_ci95_high'],permuted['delta_ci95_high'])

    def test_incomplete_boot_group_is_rejected(self):
        with self.assertRaises(ValueError):exact_intervals([1,2,3],[1,2,3,4])

if __name__=='__main__':unittest.main()
