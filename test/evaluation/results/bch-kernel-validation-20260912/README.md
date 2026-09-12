# Complete BCH kernel-driver validation records

`bch-kernel-evidence.tar.gz` preserves the selected original records of three
attempts, under their original `bch-kernel-qemu-20260912-attemptNN` names.
The interpretation is in [the evidence note](../../bch-kernel-evidence.md).

- Attempt01 failed before driver loading: the inherited BusyBox `taskset`
  lacks `-c`. Provider modules unloaded normally. Its failure and consumed
  wrapper are retained.
- Attempt02 passed all 10,752 decode checks with `measure=0` and no timing rows.
- Attempt03 passed all 10,752 decode checks and the complete 1,056 timing rows
  with `measure=1`, 11 rounds and a 10 ms calibration target. These private KVM
  times validate the collector, not a paper performance claim.

The archive includes original source snapshots, exact consumed provider/driver
modules, compiler commands, guest wrappers/auditor, kernel-package identity,
raw status/vectors/results, API addresses and module ownership, dmesg,
reference-count observations and normal unload logs. It excludes the ext4
images, shared kernel/initramfs, duplicate intermediate object files and Python
bytecode. Those local run directories remain intact. `archive-selection.json`
lists the preserved paths and the archive identity.

Replay independently without kernel access:

```sh
bch_replay_dir=$(mktemp -d /tmp/bch-kernel-replay.XXXXXX)
tar -xzf test/evaluation/results/bch-kernel-validation-20260912/bch-kernel-evidence.tar.gz -C "$bch_replay_dir"
python3 test/evaluation/bch_kernel_audit.py "$bch_replay_dir/bch-kernel-qemu-20260912-attempt02/evidence/validation" --measure 0
python3 test/evaluation/bch_kernel_audit.py "$bch_replay_dir/bch-kernel-qemu-20260912-attempt03/evidence/validation" --measure 1
```

The auditor checks individual seeded input records, all backend/mode output
locations and restoration flags, and the full measurement matrix and order.
It does not infer performance causation or page-registration lifetime behavior.
The separate [baseline archive](../bch-kernel-baselines-20260912/README.md)
records stock/debug ELF identity and compilation differences.
