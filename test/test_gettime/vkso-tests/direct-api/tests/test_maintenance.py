#!/usr/bin/env python3
"""Tool-only upgrades and scoped builds; never boot or load a module."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import workflow
import bundle
import rebuild

class RestoreTests(unittest.TestCase):
    def shell(self, body):
        source=(HERE.parent/'baremetal/collect-case.sh').read_text()
        functions=source[source.index('saved_paths=()'):source.index('set_value /sys/')]
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,DIRECT_OUT=tmp+'/absent',TEST_FILE=tmp+'/setting')
            env.pop('SUDO_UID',None);env.pop('SUDO_GID',None)
            return subprocess.run(['bash','-c','set -euo pipefail\n'+functions+'\n'+body],env=env,capture_output=True,text=True)

    def test_unchanged_value_never_saved_or_written(self):
        p=self.shell('echo 1 >"$TEST_FILE"\nset_value "$TEST_FILE" 1\ntest ${#saved_paths[@]} -eq 0\n')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_changed_value_restored(self):
        p=self.shell('echo 0 >"$TEST_FILE"\nset_value "$TEST_FILE" 1\ntest ${#saved_paths[@]} -eq 1\n')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_no_redundant_restore_write(self):
        p=self.shell('echo 0 >"$TEST_FILE"\nset_value "$TEST_FILE" 1\necho 0 >"$TEST_FILE"\nprintf() { return 77; }\n')
        self.assertEqual(p.returncode,0,p.stderr)

    def test_real_restore_failure_is_failure(self):
        p=self.shell('echo 0 >"$TEST_FILE"\nset_value "$TEST_FILE" 1\nprintf() { return 77; }\n')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('failed to restore',p.stderr)

class WorkflowTests(unittest.TestCase):
    def fixture(self, root):
        here=root/'direct-api';here.mkdir()
        bare=root/'baremetal';bare.mkdir()
        for name in ('collect-case.sh','experiment.sh','boot-once.sh','verify-packages.sh'):(bare/name).write_text('old')
        (bare/'experiment.conf').write_text('REPEATS=31\n')
        (here/'collect.py').write_text('old')
        (here/'time_bench.c').write_text('benchmark')
        pkg=root/'package';(pkg/'direct').mkdir(parents=True)
        (pkg/'direct/build.json').write_text(json.dumps({'protocol':bundle.PROTOCOL,'source_hashes':{'direct-api/time_bench.c':bundle.sha256(here/'time_bench.c')}}))
        campaign=root/'campaign';campaign.mkdir()
        return here,pkg,campaign

    def test_script_update_snapshots_without_package_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            here,pkg,root=self.fixture(Path(tmp));before=bundle.sha256(pkg/'direct/build.json')
            first=workflow.snapshot(root,here,[pkg],{'REPEATS':'31'})
            (here/'collect.py').write_text('fixed')
            with self.assertRaisesRegex(ValueError,'refresh-tools'):workflow.current_matches(root/'tool-revisions'/first,here)
            second=workflow.snapshot(root,here,[pkg],{'REPEATS':'31'})
            self.assertNotEqual(first,second)
            workflow.current_matches(root/'tool-revisions'/second,here)
            self.assertEqual(before,bundle.sha256(pkg/'direct/build.json'))
            self.assertEqual((root/'tool-revisions'/first/'direct-api/collect.py').read_text(),'old')

    def test_compiled_change_cannot_use_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            here,pkg,root=self.fixture(Path(tmp));(here/'time_bench.c').write_text('new computation')
            with self.assertRaisesRegex(ValueError,'compiled input'):workflow.snapshot(root,here,[pkg],{'REPEATS':'31'})

    def test_config_change_cannot_use_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            here,pkg,root=self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,'config changed'):workflow.snapshot(root,here,[pkg],{'REPEATS':'15'})

    def test_snapshot_tampering_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            here,pkg,root=self.fixture(Path(tmp));rev=workflow.snapshot(root,here,[pkg],{'REPEATS':'31'})
            (root/'tool-revisions'/rev/'direct-api/collect.py').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'modified'):workflow.validate(root/'tool-revisions'/rev)

    def test_selective_plans_never_start_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)/'parent';package.mkdir()
            for variant in ('normal','no-retpoline'):
                (package/'boot-manifest.txt').write_text('build_variant='+variant+'\ncc_version=11.4.0\n')
                for backend in ('raw','vkso','bench'):
                    target=backend+'-'+variant
                    with patch.object(rebuild,'check',return_value={}), \
                         patch.object(rebuild.workflow,'compatible'), \
                         patch.object(rebuild.subprocess,'check_output',return_value='11.4.0\n'), \
                         patch.object(rebuild,'run') as command, \
                         patch.object(sys,'argv',['rebuild',target,'--package',str(package),
                                      '--out',str(Path(tmp)/target),'--plan']):
                        rebuild.main()
                        command.assert_not_called()
                    self.assertFalse((Path(tmp)/target).exists())

    def test_inventory_does_not_hash_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'image').write_text('IMAGE');(p/'SHA256SUMS').write_text('stale')
            rebuild.inventory(p)
            self.assertEqual(bundle.verify_sums(p),{'image':bundle.sha256(p/'image')})

if __name__=='__main__':unittest.main(verbosity=2)
