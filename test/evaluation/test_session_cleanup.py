"""Exercise the real shell cleanup functions with local command stubs."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(path, name):
    source = path.read_text()
    start = source.index(name + '() {')
    end = source.index('\n}', start) + 2
    return source[start:end]


class CleanupTests(unittest.TestCase):
    def session(self, child_status, state, restore_status=0, unload_status=0, foreign=False):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            if state:
                (base / 'state').write_text('notify_fifo=' + str(base / ('other-notify' if foreign else 'notify')) + '\n')
            code = function(ROOT / 'vkso', 'setup_event') + '\n' + function(ROOT / 'vkso', 'hold_state_owned') + '\n' + function(ROOT / 'vkso', 'cleanup_session')
            script = r'''
HOLD_ACTIVE=1
PAGE_MODULE_LOADED_BY_US=1
HOLD_PID_FILE="$1/pid"
HOLD_STATE_FILE="$1/state"
HOLD_NOTIFY_PATH="$1/notify"
HOLD_NOTIFY_DIR=""
HOLD_NOTIFY_FD=""
HOLD_NOTIFY_DONE=0
METADATA_DIR="$1"
CURRENT_SCRATCH=""
MANAGER_BIN=manager
log() { echo "$*"; }
metadata_value() { echo "$1-value"; }
as_root() {
    echo "command $*" >> "$1_UNUSED/events"
    if [[ "$1" == rmmod ]]; then return "$unload_status"; fi
    if (( restore_status == 0 )); then rm -f "$HOLD_STATE_FILE"; fi
    return "$restore_status"
}
'''.replace('"$1_UNUSED/events"', '"$event_dir/events"')
            script += '\nevent_dir="$1"\nchild_status="$2"\nrestore_status="$3"\nunload_status="$4"\n'
            script += '\n' + code + '\n(exit "$child_status") &\nHOLD_WRAPPER_PID=$!\ncleanup_session 0\n'
            result = subprocess.run(['bash', '-c', script, 'cleanup-test', directory,
                                     str(child_status), str(restore_status), str(unload_status)],
                                    capture_output=True, text=True, timeout=10)
            events = (base / 'events').read_text() if (base / 'events').exists() else ''
            if foreign:
                self.assertTrue((base / 'state').exists())
                self.assertIn('other-notify', (base / 'state').read_text())
            return result.returncode, events

    def test_success_unloads_page_module(self):
        status, events = self.session(0, False)
        self.assertEqual(status, 0)
        self.assertIn('rmmod page_cache_replace', events)

    def test_restore_error_reaches_caller_and_retains_module(self):
        status, events = self.session(23, True, restore_status=7)
        self.assertNotEqual(status, 0)
        self.assertIn('manager restore', events)
        self.assertNotIn('rmmod', events)

    def test_missing_state_does_not_hide_manager_error(self):
        status, events = self.session(23, False)
        self.assertNotEqual(status, 0)
        self.assertNotIn('rmmod', events)

    def test_module_unload_failure_reaches_caller(self):
        status, events = self.session(0, False, unload_status=7)
        self.assertNotEqual(status, 0)
        self.assertIn('rmmod page_cache_replace', events)

    def test_competing_launch_preserves_foreign_state(self):
        status, events = self.session(1, True, foreign=True)
        self.assertNotEqual(status, 0)
        self.assertNotIn('kill', events)
        self.assertNotIn('manager restore', events)
        self.assertNotIn('rmmod', events)

    def test_algorithm_owner_cleanup(self):
        for algorithm in ('test_lz4', 'test_BCH', 'test_xz'):
            for run_status, unload_status in ((0, 0), (7, 0), (0, 9)):
                with self.subTest(algorithm=algorithm, run_status=run_status, unload_status=unload_status):
                    cleanup = function(ROOT / 'test' / algorithm / 'run.sh', 'cleanup')
                    script = '''loaded_by_us=1
sudo() { echo "UNLOAD $*"; return "$1_UNUSED"; }
sudo_cmd() { sudo "$@"; }
'''.replace('"$1_UNUSED"', str(unload_status))
                    script += cleanup + '\ntrap cleanup EXIT\nexit ' + str(run_status) + '\n'
                    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, timeout=5)
                    self.assertEqual('UNLOAD' in result.stdout, run_status == 0)
                    self.assertEqual(result.returncode == 0, run_status == unload_status == 0)


if __name__ == '__main__':
    unittest.main()
