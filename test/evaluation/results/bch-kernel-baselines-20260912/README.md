# Installed exact119 BCH baseline evidence

This directory contains small read-only captures of installed Ubuntu119 BCH
binary provenance, public interfaces, stock compilation attributes, and the
existing complete adapted owner consumed by BCH resource attempt03. No module
was loaded and no source was compiled or downloaded for this capture.

The interpretation and comparison boundaries are in
[`../../bch-kernel-baselines.md`](../../bch-kernel-baselines.md).
`result.json` reports only binary/header/source-pair checks, not a new runtime
or performance result. The third matched-source-kernel baseline is implemented
by a separate task; this directory does not claim its build or run completed.

To capture the same installed inputs again into a fresh directory, run from
the repository (Python 3 and pyelftools are required):

```sh
python3 test/evaluation/results/bch-kernel-baselines-20260912/capture.py --output /tmp/bch-kernel-baselines-review
```

The script reads the exact installed paths and the existing attempt03 owner;
it writes only to `--output`. It records `dpkg-query`, `modinfo`, ELF note and
source-diff command outputs, extracts selected ELF/DWARF fields, and compares
all 17 allocated stock/debug sections, the public header, and consumed/current
owner sources. `commands.json` and `identity.json` retain the input identity and
capture commands. No full DWARF dump, kernel image, source tarball or large
module binary is copied into this directory.
