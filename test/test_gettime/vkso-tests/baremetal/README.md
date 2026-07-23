# Raw vDSO / VKSO native x86-64 bare-metal experiment

This suite builds and boots two Linux 5.15.198 images from one resolved
bare-metal configuration:

```text
raw image:   native x86-64 vDSO + native syscall implementation
VKSO image:  no native vDSO + shared VKSO core + VKSO syscall adapter
```

The VKSO user path uses the project page-replacement mechanism and the same
hand-written wrapper validated by M27.  `CONFIG_VKSO_TIME_TEST` is disabled;
no test probe is present in the measured kernel.

## 1. Build the images and test package

The default base config is the known-bootable config already installed on
`intelnuczzk`.  It retains the machine's drivers, then removes debug
instrumentation, IA32/x32/vsyscall and enables module support for the project
page mapper.

```sh
cd /home/zzk/BinaryKernelCodeMapping

test/test_gettime/vkso-tests/baremetal/build-images.sh
```

Optional paths:

```sh
BASE_CONFIG=/path/to/known-bootable.config \
RAW_SOURCE=/path/to/linux-5.15.198 \
BUILD_ROOT=/tmp/vkso-baremetal-build \
test/test_gettime/vkso-tests/baremetal/build-images.sh
```

The completed package is linked as:

```text
test/test_gettime/vkso-tests/baremetal/artifacts/current
```

It contains both `bzImage` files, their exact configs, `libkernel.so`, page
map, replacement module/manager, functional matrices, performance benchmark,
scripts, manifest and checksums.

Run a functional preflight on both packaged images before changing GRUB:

```sh
test/test_gettime/vkso-tests/baremetal/qemu-preflight.sh
```

This executes the ABI/path matrices and VKSO replacement lifecycle.  Its
timing rows are smoke tests only, not performance results.

## 2. Install the GRUB entries

This is the only preparation step requiring the user's sudo password:

```sh
test/test_gettime/vkso-tests/baremetal/install-grub.sh
```

The installer:

- verifies the package checksums;
- backs up any existing experiment images and GRUB script;
- installs raw/VKSO images and configs in `/boot`;
- derives the current `/boot` UUID and root PARTUUID;
- writes IDs `vkso-time-raw` and `vkso-time-vkso`;
- uses identical experiment arguments, including `nokaslr`, TSC,
  `nosmt`, CPU 2 isolation, full dynticks, IRQ affinity, idle polling,
  disabled deep C-states and watchdogs;
- regenerates and validates `grub.cfg`.

The scripts use `grub-reboot`, so the normal Ubuntu entry remains the default
after each one-shot experiment boot.

## 3. Collect the raw result

```sh
test/test_gettime/vkso-tests/baremetal/boot-raw.sh
```

After the reboot:

```sh
cd /home/zzk/BinaryKernelCodeMapping
sudo test/test_gettime/vkso-tests/baremetal/collect.sh
```

The script prints an `active_run_id` and records it for the VKSO phase.

## 4. Collect the VKSO result and compare

```sh
test/test_gettime/vkso-tests/baremetal/boot-vkso.sh
```

After the reboot:

```sh
cd /home/zzk/BinaryKernelCodeMapping
sudo test/test_gettime/vkso-tests/baremetal/collect.sh
```

The VKSO phase validates and activates `libkernel.so`, runs the tests, then
restores the page cache and unloads the module even on failure.  It compares
the paired raw result and creates:

```text
results/<run-id>/
├── raw/
│   ├── functional.log
│   ├── functional.matrix
│   ├── perf.csv
│   ├── seq.csv
│   └── environment.txt
├── vkso/
│   ├── functional.log
│   ├── functional.matrix
│   ├── perf.csv
│   ├── seq.csv
│   ├── layout.csv
│   └── environment.txt
├── path-summary.csv
├── research-questions.csv
└── SUMMARY.md
```

It also creates `results/<run-id>.tar.gz`, which is the file to copy for
analysis.

## Functional coverage

The same M27 program is run against raw vDSO and VKSO.  The normalized
matrices must be byte-identical.  Coverage includes:

- `clock_gettime`: realtime, monotonic, monotonic-raw, boottime, TAI, both
  coarse clocks, process/thread CPU clocks, alarm clocks, invalid ID and
  NULL behavior;
- all high-resolution/coarse/fallback/invalid/NULL `clock_getres` cases;
- all four `gettimeofday` pointer combinations;
- `time(NULL)` and `time(&value)`;
- all `getcpu` pointer/cache combinations, multiple CPUs and threads;
- seccomp proof of fast path versus syscall fallback;
- time namespace exec, setns/commit, frozen offsets and per-MM context.

## Performance coverage

Each batch is pinned to isolated CPU 2.  Path order rotates on every repeat.
The default is 500,000 calls per sample, 31 samples, 10,000 warmup calls and
PMU enabled.

The result directly answers:

1. `vkso_wrapper` versus `vkso_core` overhead for each supported API.
2. Raw vDSO versus VKSO core/wrapper on TSC high-resolution clocks.
3. Raw syscall versus VKSO syscall, measuring the shared-kernel-core effect.
4. Raw/VKSO seq conflict rate using an uninstrumented userspace observer of
   the same seq window.
5. End-to-end MONOTONIC_RAW cycles/instructions/L1D/LLC data.
6. An isolated cold-cache old-straddled versus new-aligned raw layout A/B.

The seq observer does not modify production code and therefore reports the
retry opportunity rate, not a hidden counter inside the production function.
The synthetic layout A/B isolates the layout effect; the actual
MONOTONIC_RAW PMU rows remain the end-to-end evidence.

Useful overrides must be identical for both boots:

```sh
sudo CPU=2 ITERATIONS=1000000 REPEATS=51 WARMUP=20000 \
  PMU=1 SEQ_ITERATIONS=500000000 LAYOUT_ITERATIONS=500000 \
  test/test_gettime/vkso-tests/baremetal/collect.sh <optional-run-id>
```

Do not use QEMU timing as a performance result.  QEMU remains a functional
preflight only.
