"""Check the completed budget closeout before new, separately named work."""
import hashlib
import json
from pathlib import Path

RUNS = Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
ROOT = Path('/home/zzk/BinaryKernelCodeMapping')

def verify():
    closeout = RUNS / 'budget-closeout-01'
    stopped = json.loads((closeout / 'stopped.json').read_text())
    assert stopped['task_modules_unloaded'] and not stopped['background_tasks_alive']
    audit = json.loads((closeout / 'audit.json').read_text())
    assert audit['status'] == 'complete' and audit['observations'] == 4580
    assert hashlib.sha256((closeout / 'analysis.json').read_bytes()).hexdigest() == audit['analysis_sha256']
    reg = json.loads((ROOT / 'test/section65/squashfs/optimization-20261030-01/confirmation-registration.json').read_text())
    for name, digest in reg['identities'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    task_modules = {'vkso_sq_core', 'vkso_squashfs', 'page_cache_replace', 'vkso_kernel_reader'}
    assert not task_modules.intersection(l.split()[0] for l in Path('/proc/modules').read_text().splitlines())
    return {'status': 'verified', 'frozen_inputs': len(reg['identities']),
            'previous_closeout': str(closeout), 'previous_observations': 4580}

if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
