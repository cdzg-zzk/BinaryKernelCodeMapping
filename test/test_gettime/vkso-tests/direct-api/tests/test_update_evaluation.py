"""Verify complete-cost accounting independently of the formal sample values."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from update_evaluation import band, components

class Decomposition(unittest.TestCase):
    def test_tail_is_not_double_counted(self):
        # Raw mean=400, VKSO mean=260; explicit four-term arithmetic oracle.
        r=band(np.array([100,100,1000]),150,300)
        v=band(np.array([80,200,500]),150,300)
        z=components(r,v)
        self.assertAlmostEqual(z['delta'],-140)
        self.assertAlmostEqual(z['low_contribution'],-10)
        self.assertAlmostEqual(z['high_capped_contribution'],-25)
        self.assertAlmostEqual(z['occupancy_contribution'],185/3)
        self.assertAlmostEqual(z['tail_contribution'],-500/3)
        self.assertAlmostEqual(sum(z[k] for k in z if k.endswith('contribution')),-140)

    def test_cut_and_tail_boundary_do_not_change_full_cost(self):
        r=np.array([70,85,95,110,130,180,320,1900])
        v=np.array([60,75,90,120,140,160,350,700])
        for cr,cv,cap in [(100,100,300),(120,100,200),(90,130,180),(110,120,240)]:
            z=components(band(r,cr,cap),band(v,cv,cap))
            self.assertAlmostEqual(z['delta'],float(v.mean()-r.mean()))
            self.assertAlmostEqual(z['residual'],0,places=10)

    def test_empty_band_is_not_fabricated(self):
        with self.assertRaises(ValueError):band(np.array([70,80]),100,300)
        with self.assertRaises(ValueError):band(np.array([70,80,200]),300,200)

if __name__=='__main__':unittest.main()
