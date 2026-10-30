#!/usr/bin/env python3
"""Run matched full-image tasks through LKL, copied-core FUSE and VKSO FUSE."""
import argparse
import contextlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys

from probe import lkl_argv, memory, mounted

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=ROOT / 'test/evaluation-local/packages/iso9660-native-optimized-20261029')
    parser.add_argument('--frontend', type=Path, default=SECTION / 'build/lkl/vkso-isofuse-matched')
    parser.add_argument('--bridge', type=Path, help='user adapter; defaults to the immutable native package')
    parser.add_argument('--uncached-bridge', type=Path, help='add a shared-core ablation using this older adapter')
    parser.add_argument('--lkl', action='append', required=True, help='NAME=MEMORY_MIB:BINARY')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--blocks', type=int, default=8)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--client-cpu', type=int, default=1)
    parser.add_argument('--server-cpu', type=int, default=2)
    parser.add_argument('--functional', action='store_true')
    args = parser.parse_args()
    args.package = args.package.resolve()
    args.frontend = args.frontend.resolve()
    args.bridge = (args.bridge or args.package / 'libiso-bridge.so').resolve()
    if args.uncached_bridge: args.uncached_bridge = args.uncached_bridge.resolve()
    profiles = {}
    for item in args.lkl:
        label, rest = item.split('=', 1)
        mib, binary = rest.split(':', 1)
        assert label.startswith('lkl-') and label not in profiles
        profiles[label] = dict(memory_mib=int(mib), binary=str(Path(binary).resolve()))
    assert args.blocks >= 1 and args.repeats >= 1
    spec = importlib.util.spec_from_file_location('iso_native_protocol', args.package / 'run.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    sys.path.insert(0, str(args.package))
    native.VARIANTS = ('original', 'copied-fuse', 'vkso-fuse',
                       *(('vkso-uncached',) if args.uncached_bridge else ()), *profiles)
    os.environ['PATH'] = str(args.package / 'bin') + ':' + os.environ['PATH']
    os.environ['LD_LIBRARY_PATH'] = str(args.package)
    os.environ['VKSO_ISOFUSE_STATS'] = '1'

    class Campaign(native.Campaign):
        def preflight(self):
            self.daemon_index = 0
            self.last_resources = None
            super().preflight()
            (self.out / 'daemons').mkdir()
            path = self.out / 'environment.json'
            environment = json.loads(path.read_text())
            environment['comparison'] = dict(variants=list(native.VARIANTS), lkl=profiles,
                frontend=str(args.frontend), bridge=str(args.bridge),
                uncached_bridge=str(args.uncached_bridge) if args.uncached_bridge else None,
                fuse_policy=dict(entry_timeout=0, attr_timeout=0,
                negative_timeout=0, use_ino=1, nullpath_ok=1, single_threaded=True),
                resource_units='memory fields in KiB, except Threads; startup seconds include a completed root getattr',
                preparation='VKSO owner is the previously verified optimized binary; explicit bridge/frontend paths record user adapter variants',
                versions='ISO preparation uses Linux 5.15.198; LKL uses pinned Linux 6.12 fork; comparisons are complete implementations, not pure mechanism cost')
            native.write(path, environment)

        def stage(self, name):
            if name == 'verify all five paths against original kernel':
                name = f'verify all {len(native.VARIANTS)} paths against original kernel'
            super().stage(name)

        @contextlib.contextmanager
        def mounted(self, variant, image, norock=False):
            self.last_resources = None
            if variant == 'original':
                with super().mounted(variant, image, norock) as child:
                    yield child
                return
            if variant in profiles:
                profile = profiles[variant]
                command = lkl_argv(profile['binary'], profile['memory_mib'], image, self.mount, norock)
            else:
                core = self.copied if variant == 'copied-fuse' else self.library
                bridge = args.uncached_bridge if variant == 'vkso-uncached' else args.bridge
                command = [str(args.frontend), str(core), str(bridge),
                           str(image), str(int(norock)), str(self.mount),
                           'entry_timeout=0,attr_timeout=0,negative_timeout=0']
            command = ['taskset', '-c', str(args.server_cpu)] + command
            self.daemon_index += 1
            log = self.out / 'daemons' / f'{self.daemon_index:04d}-{variant}.log'
            with mounted(command, self.mount, log) as (child, startup):
                record = dict(startup_seconds=startup, before=memory(child.pid), command=command,
                              log=str(log.relative_to(self.out)))
                yield child
                record['after'] = memory(child.pid)
                self.last_resources = record
            assert child.returncode == 0, (variant, child.returncode, log)

        def correctness(self):
            from reference_guest import manifest
            cases = json.loads((args.package / 'reference/result.json').read_text())['cases']
            proof = []
            for variant in native.VARIANTS:
                for index, case in enumerate(cases):
                    self.stage(f'verify: {variant} {case["image"]} {case["mode"]}')
                    with self.mounted(variant, args.package / 'images' / case['image'], case['mode'] == 'norock') as child:
                        rows = manifest(self.mount)
                        expected = json.loads((args.package / 'reference' / case['manifest']).read_text())
                        assert rows == expected, (variant, case, 'reference mismatch')
                        if variant in ('copied-fuse', 'vkso-fuse', 'vkso-uncached') and index == 0:
                            shared = variant != 'copied-fuse'
                            self.pfns(child.pid, self.library if shared else self.copied,
                                      shared, 'pfns-' + variant)
                    proof.append(dict(variant=variant, **case))
            oracle = None
            for variant in native.VARIANTS:
                self.stage(f'verify: {variant} kernel-include.iso')
                with self.mounted(variant, args.package / 'images/kernel-include.iso'):
                    rows = manifest(self.mount)
                    if oracle is None:
                        oracle = rows
                        native.write(self.out / 'kernel-include-reference.json', rows)
                    assert rows == oracle, (variant, 'include tree mismatch')
                proof.append(dict(variant=variant, image='kernel-include.iso', entries=len(rows)))
            native.write(self.out / 'correctness.json', dict(status='pass', cases=proof))

        def measure(self, variant, image, workload, block, repeat, phase):
            super().measure(variant, image, workload, block, repeat, phase)
            resource = dict(variant=variant, image=image.name, workload=workload, block=block,
                            repeat=repeat, phase=phase, process=self.last_resources)
            with (self.out / 'resources.jsonl').open('a') as stream:
                stream.write(json.dumps(resource) + '\n')

        def timings(self):
            super().timings()
            comparisons = []
            pairs = [('copied-fuse', 'vkso-fuse'), ('original', 'vkso-fuse')]
            pairs += [(label, 'vkso-fuse') for label in profiles]
            if args.uncached_bridge: pairs.append(('vkso-uncached', 'vkso-fuse'))
            groups = {}
            for row in self.rows:
                key = (row['image'], row['workload'], row['block'], row['variant'])
                groups.setdefault(key, []).append(row['wall_seconds'])
            for image, workload in sorted({(r['image'], r['workload']) for r in self.rows}):
                for baseline, treatment in pairs:
                    ratios = [statistics.median(groups[(image, workload, b, treatment)]) /
                              statistics.median(groups[(image, workload, b, baseline)]) for b in range(args.blocks)]
                    logs = [math.log(value) for value in ratios]
                    rng = random.Random(20261029)
                    bootstrap = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(10000))
                    comparisons.append(dict(image=image, workload=workload, baseline=baseline, treatment=treatment,
                        blocks=len(ratios), paired_ratios=ratios, geometric_mean_time_ratio=math.exp(statistics.mean(logs)),
                        bootstrap_95_percent=[bootstrap[250], bootstrap[9749]] if len(ratios) >= 4 else None,
                        direction='ratio > 1 means VKSO takes longer than the listed baseline'))
            native.write(self.out / 'summary.json', dict(status='complete', functional_only=args.functional,
                                                         comparisons=comparisons))

    campaign = Campaign(args)
    if args.functional:
        campaign.status['scope'] = 'host runner functional preflight; no performance conclusion'
    raise SystemExit(campaign.run())


if __name__ == '__main__':
    main()
