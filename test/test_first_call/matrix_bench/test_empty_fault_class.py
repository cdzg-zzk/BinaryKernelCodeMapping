"""A real C statistics path must preserve calls when its expected class is empty."""
from pathlib import Path
import csv,subprocess,tempfile,unittest
from analyze_first_touch import audit
from test_batch_archiving import fixture_environment,RUNNER

class EmptyFaultClassTest(unittest.TestCase):
    def test_zero_retention_is_rejected_even_at_zero_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);environment=fixture_environment(root)
            original=Path(__file__).with_name('benchmark_first_touch.c').resolve()
            harness=root/'empty.c'
            harness.write_text('#define main original_main\n#include "'+str(original)+'"\n#undef main\n'+r'''
int main(int argc, char **argv) {
    const struct target_spec *target = NULL;
    const char *path = NULL;
    int count = 0, opt;
    while ((opt=getopt(argc,argv,"t:s:n:o:"))!=-1) {
        if (opt=='t') target=find_target(optarg);
        if (opt=='n') count=atoi(optarg);
        if (opt=='o') path=optarg;
    }
    if (!target || !path || count!=10) return 2;
    struct sample samples[10];
    for (int i=0;i<10;++i) samples[i]=(struct sample){.cycles=100+i,.minflt=1,.majflt=0,.preparation_status=0};
    FILE *out=fopen(path,"wx"); if(!out) return 2;
    if(write_samples(out,target,COND_HOT,samples,10)) return 2;
    print_statistics(target,COND_HOT,samples,10);
    return 0;
}
''')
            subprocess.run(['gcc','-O2',str(harness),'-ldl','-lm','-o',str(root/'benchmark_first_touch')],check=True,capture_output=True)
            result=subprocess.run(['bash',str(RUNNER)],cwd=root,env={**environment,'MAX_ATTEMPTS':'1','THRESHOLD_PCT':'0'},
                                  text=True,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,2,result.stderr)
            report=audit(root/'records');self.assertFalse(report['complete'])
            for target in ('native','stub'):
                group=report['groups'][target+'/hot']
                self.assertEqual(group['views']['all_prepared_calls']['calls'],10)
                self.assertEqual(group['views']['all_prepared_calls']['mean'],104.5)
                self.assertEqual(group['views']['expected_fault_calls'],{'calls':0})
                self.assertEqual(group['decisions'],{'rejected':1})
                self.assertIsNone(group['mean_accepted_batch_statistics'])
            with (root/'records/attempts.csv').open() as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual([r['reason'] for r in rows],['no_expected_fault_samples']*2)
if __name__=='__main__': unittest.main()
