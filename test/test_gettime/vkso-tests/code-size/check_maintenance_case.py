#!/usr/bin/env python3
"""Check the actual pre/post helper in aa1855e on its admitted input domain.

This is host arithmetic evidence for the maintenance example. Whole current
reader and adapter behavior is covered separately by test_kernel_contract.py;
physical sharing is evidenced by the recorded bare-metal campaign.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from audit_current import REPO, OUT

DIRECT = REPO / 'test/test_gettime/vkso-tests/direct-api/tests'
sys.path.insert(0, str(DIRECT))
from test_kernel_contract import definition

COMMIT = 'aa1855e812107757f57ef68fc537f91c48c8034c'
PATH = 'test/test_gettime/linux-5.15.198-vkso/kernel/time/vkso_time_internal.h'


def main():
    bodies = []
    for ref, name in [(COMMIT + '^', 'before'), (COMMIT, 'after')]:
        text = subprocess.check_output(['git', 'show', ref + ':' + PATH], cwd=REPO, text=True)
        bodies.append(definition(text, 'vkso_cycle_delta').replace('vkso_cycle_delta', name))
    prefix = '#include <stdint.h>\n#include <assert.h>\n#include <stdio.h>\n' \
             'typedef uint64_t u64;\n#define U64_MAX UINT64_MAX\n' \
             '#define likely(x) (x)\n'
    main_c = r'''
int main(void) {
    const u64 edges[] = {0,1,2,UINT32_MAX,UINT32_MAX+1ULL,
        (1ULL<<63)-1,(1ULL<<63),(1ULL<<63)+1,UINT64_MAX-1,UINT64_MAX};
    unsigned long checks = 0;
    for (unsigned i=0;i<10;i++) for (unsigned j=0;j<10;j++) {
        u64 c=edges[i],last=edges[j],want=c>last?c-last:0;
        assert(before(c,last,UINT64_MAX)==want && after(c,last)==want); checks++;
    }
    u64 rng=0x412C10C;
    for (unsigned i=0;i<100000;i++) {
        rng=rng*6364136223846793005ULL+1442695040888963407ULL;u64 c=rng;
        rng=rng*6364136223846793005ULL+1442695040888963407ULL;u64 last=rng;
        u64 want=c>last?c-last:0;
        assert(before(c,last,UINT64_MAX)==want && after(c,last)==want);checks++;
    }
    printf("helper_equivalence=PASS cases=%lu mask=UINT64_MAX\n",checks);
}
'''
    source = prefix + '\n'.join(bodies) + main_c
    with tempfile.TemporaryDirectory(prefix='clocktime-maintenance-') as temp:
        p = Path(temp)
        (p / 'case.c').write_text(source)
        cmd = ['gcc', '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(p / 'case.c'), '-o', str(p / 'case')]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        result = subprocess.check_output([str(p / 'case')], text=True)
    (OUT / 'maintenance-helper.c').write_text(source)
    (OUT / 'maintenance-validation.json').write_text(json.dumps({
        'commit': COMMIT, 'source_path': PATH, 'case': 'full-width cycle delta specialization',
        'input_domain': 'mask=UINT64_MAX; arbitrary 64-bit helper arguments; provider acceptance is separate',
        'result': result.strip(), 'cases': 100100,
        'compiler': subprocess.check_output(['gcc', '-dumpfullversion'], text=True).strip(),
        'production_functions_changed': ['vkso_cycle_delta', 'vkso_read_hres_time'],
        'test_functions_changed': ['vkso_cycle_delta_selftest'],
        'user_adapter_functions_changed': [], 'kernel_adapter_functions_changed': [],
        'publisher_functions_changed': [], 'mapping_functions_changed': [],
        'raw_comparison': 'x86 vDSO already specializes this operation; no claimed two-to-one patch saving',
        'scope': 'arithmetic equivalence; not a kernel boot, hardware ordering or performance experiment',
    }, ensure_ascii=False, indent=2) + '\n')
    print(result, end='')


if __name__ == '__main__':
    main()
