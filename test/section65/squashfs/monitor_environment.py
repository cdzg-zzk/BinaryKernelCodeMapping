#!/usr/bin/env python3
"""Passive environment observations; never changes host configuration."""
import argparse
import collections
import json
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--until',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as out:
        while True:
            procs=collections.Counter()
            for proc in Path('/proc').iterdir():
                if proc.name.isdigit():
                    try:procs[(proc/'comm').read_text().strip()]+=1
                    except OSError:pass
            paths=[Path('/sys/devices/system/cpu/intel_pstate/no_turbo'),Path('/sys/devices/system/cpu/smt/control')]
            for field in ['scaling_governor','scaling_cur_freq','scaling_min_freq','scaling_max_freq']:
                paths.extend(Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/'+field))
            queue=json.loads(a.until.read_text())
            record=dict(time=time.time(),until_status=queue['status'],loadavg=Path('/proc/loadavg').read_text().strip(),
                frequency={str(p):p.read_text().strip() for p in paths if p.exists()},
                process_counts=dict(procs),cpu_stat=Path('/proc/stat').read_text(),
                pressure={p.name:p.read_text() for p in Path('/proc/pressure').glob('*')})
            out.write(json.dumps(record)+'\n');out.flush()
            if queue['status']!='running':break
            time.sleep(60)


if __name__=='__main__':main()
