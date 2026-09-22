#!/usr/bin/env python3
"""Replay manager retirement and its recovery windows from the full matrix."""
from pathlib import Path
import argparse
import json
import re

from registration_notification_audit import audit as notification_audit


def audit(directory):
    directory = Path(directory).resolve()
    notifications = notification_audit(directory)
    result = json.loads((directory / 'result.json').read_text())
    guest = result['guest_record']
    checks = guest['checks']
    validation = directory / 'evidence/validation'
    owner = guest['owner']
    assert checks['manager_lost_commit_and_release_ack']
    assert checks['manager_failure_retains_state_and_retries']
    assert checks['manager_crash_reconnect_release']
    for name in ('released-confirmed', 'forgotten-confirmed'):
        checkpoint = checks['checkpoint_' + name]
        before = checkpoint['before_recovery']
        after = checkpoint['after_recovery']
        assert before['transaction'] == after['transaction'] == checkpoint['transaction']
        assert before['applied'] == after['applied'] == 0
        assert (before['status'], before['state']) == ((0, 4) if name == 'released-confirmed' else (-2, 0))
        assert (after['status'], after['state']) == (-2, 0)
        assert checkpoint['refs_while_manager_socket_open'] == {owner: 0, 'page_cache_replace': 2}
        state = (validation / f'checkpoint-{name}.state').read_text()
        assert int(re.search(r'^transaction_id=(\d+)$', state, re.M)[1]) == checkpoint['transaction']
        log = (validation / f'checkpoint-{name}-recovery.log').read_text()
        assert 'Cleared manager-added immutable flag' in log
        if name == 'released-confirmed':
            assert 'operation=6 ' in log and 'status=0 state=4' in log
        else:
            assert 'absent; no active bindings to release' in log
    lost = checks['manager_lost_forget_ack']
    assert lost['status'] == -2 and lost['state'] == 0
    log = (validation / 'forget-lost-ack-restore.log').read_text()
    assert f'recovered_absence id={lost["transaction"]} operation=6' in log
    assert 'operation=4 ' in log and 'status=-2 state=0' in log
    ids = set()
    for path in validation.rglob('*.log'):
        ids.update(int(tid) for tid in re.findall(r'^VKSO_TRANSACTION id=(\d+) operation=1\b', path.read_text(), re.M))
    missing = checks['manager_terminal_records_absent']
    assert len(missing) == len(ids) and {r['transaction'] for r in missing} == ids
    assert all(r['operation'] == 4 and r['status'] == -2 and r['state'] == 0 and r['applied'] == 0 for r in missing)
    source = (directory / 'source/manager.cpp').read_text()
    assert 'r.operation = VKSO_FORGET;' in source and 'result.status == -ENOENT && result.state == VKSO_UNKNOWN' in source
    return dict(status='pass', boot_id=guest['boot_id'], manager_transactions_absent=len(ids),
                recovery_checkpoints=['released-confirmed', 'forgotten-confirmed'],
                lost_forget_reply_recovered=True, original_transaction_and_notification_matrix='pass',
                source_owner=owner, notification_audit=notifications,
                scope='terminal objects retired; allocator page return and physical net memory are not measured')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = audit(args.directory)
    (args.directory / 'retirement-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'notification_audit'}, indent=2))
