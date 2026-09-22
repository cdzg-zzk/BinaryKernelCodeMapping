"""Methodology checks: treatment blindness, both-build threshold, run hierarchy."""
import copy
import unittest
from layer3_v2 import ROOT, read_raw, select_batches, aggregate, ROUTINES

class Methodology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=read_raw(ROOT/'results/layer3')
    def test_treatment_blind(self):
        expected,_=select_batches(self.raw,{'selection_overhead_tsc':39})
        changed=copy.deepcopy(self.raw)
        for i,r in enumerate(changed):
            r['variant_cycles']=(-1)**i*1e12
            r['delta_variant_origin']=(-1)**i*1e10
        self.assertEqual(expected,select_batches(changed,{'selection_overhead_tsc':39})[0])
    def test_both_builds_and_no_fallback(self):
        raw=copy.deepcopy(self.raw)
        name=next(iter(ROUTINES));small=ROUTINES[name][0]
        for r in raw:
            if r['routine']==name and r['build']=='retpoline' and r['iterations']==small:
                r['origin_cycles']=1
        self.assertEqual(select_batches(raw,{'selection_overhead_tsc':39})[0][name],ROUTINES[name][1])
        with self.assertRaises(ValueError):select_batches(raw,{'selection_overhead_tsc':1e20})
    def test_outer_unit(self):
        rows=[]
        for run,delta in enumerate([1,2,100]):
            for repeat in range(15):
                rows.append(dict(routine='x',build='no_retpoline',variant='data_pgot',iterations=1,
                                 run_id=run,repeat=repeat,origin_cycles=100,variant_cycles=100+delta,
                                 delta_variant_origin=delta))
        outer,summary=aggregate(rows,ci=True)
        self.assertEqual(len(outer),3)
        self.assertEqual(summary[0]['outer_runs'],3)
        self.assertEqual(summary[0]['overhead_pct'],2)
        self.assertGreater(summary[0]['ci_high_pct'],90)

if __name__=='__main__':unittest.main()
