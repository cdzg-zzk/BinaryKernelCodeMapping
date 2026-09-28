# Kernel reader regression and scalar diagnostics

The historical READ campaign measures three timespec APIs. This directory also
provides **separate scalar diagnostics**, plus deterministic host and Kbuild/VM
validation for the completing kernel-reader contract. Nothing here installs a
kernel, edits GRUB, changes campaign state, or replaces a frozen package in place.

## What changed, and what deliberately did not

`vkso_time_get_root()` is a **completing** kernel adapter for supported clocks.
The fixed kernel failure callback already performs the private read and returns
success. Returning the opaque shared callee status previously retained a second
fallback in callers such as `ktime_get_ts64()`, even though the provider failure
had already been handled. The adapter now returns class support: `OK` after a
supported read completes, `NOT_SHARED` for a native-only clock. This lets normal
inlining remove that redundant branch across all callers. The getcpu adapter
similarly exposes its shared reader's unconditional-success contract; syscall
`put_user()` faults are still checked in the syscall boundary.

This is not permission to discard new errors in future implementations. A future
change to kernel callback return semantics must update this contract and its tests.
User-domain callbacks still propagate syscall errors. The shared algorithm,
context/state layout, public ABI, provider selection, namespace offset arithmetic,
TSC inline path, and user IFUNC/entry files are unchanged. Private provider fallback
and NMI/locked-context readers remain available. Scalar normalization is **not**
rewritten without target performance evidence.

## Host checks

From the repository root:

```sh
python3 -m unittest discover -s test/test_gettime/vkso-tests/direct-api/tests -p 'test_*.py' -v
python3 -m unittest discover -s test/test_gettime/vkso-tests/code-size -p 'test_audit_changes.py' -v
```

`test_kernel_contract.py` compiles the real production time core, extracts the real
ordinary callers and kernel failure callbacks, and supplies fake environment
primitives only. It checks 50,000 integer-oracle cases, carry and negative namespace
offsets, unsupported clocks, deterministic seq retry, callback completion exactly
once, no second namespace adjustment, and user error propagation. A code-generation
check compares the same callers against the pinned `09b9505` and current headers.
It does **not** validate real memory ordering, PFNs, privilege transitions or speed.

Temporary headers, fixtures and binaries live in `TemporaryDirectory` and are
removed on normal completion/failure. `VKSO_TEST_ARTIFACTS=/some/new/path` optionally
retains disassembly and source/compiler identities instead of temporary scripts.

## Real Linux 5.15.198 Kbuild and isolated VM checks

Obtain and extract the original Linux 5.15.198 release, and install GCC 11, make,
bc, bison, flex, libelf and OpenSSL development packages. For the optional smoke,
install QEMU x86 and a **statically linked** BusyBox. No root privileges are needed
by the validator itself.

```sh
python3 test/test_gettime/vkso-tests/revision/kernel-reader/validate_build.py \
  --source "$HOME/kernel-sources/linux-5.15.198" \
  --out "$HOME/vkso-validation/contract-normal" \
  --variant normal --cc gcc-11 --jobs 4 --boot-smoke
```

Repeat with `--variant no-retpoline` and a distinct output directory. Omitting
`--boot-smoke` only builds/compares objects. The original source tree and repository
are not edited; the selected tracked kernel and captured platform edits are
reconstructed in a temporary source copy. Output directories must be new.

The baseline defaults to `09b9505667f1d1c3da71ac8aaaa7d6054255bc62`. The candidate is
`HEAD`, overridable with `--head COMMIT`. Configs and compiler are paired. The
validator compiles real kernel translation units and the real measurement module,
retains disassembly and function sizes, and requires the three `.vkso.text` payloads
to be byte-identical. Object byte equality does not imply final linked addresses,
all relocations, cache placement or elapsed latency are identical.

The optional VM smoke builds a **minimal candidate test kernel**, not the NUC's
formal image. It boots QEMU TCG with TSC, then with jiffies to exercise kernel
provider fallback. Each boot checks real time/getcpu syscall behavior (including
invalid IDs and user-copy faults), loads the reader module, runs both timespec and
scalar suites, validates CSV completeness and unloads the module. TCG timings are
retained in boot logs solely as functional evidence. They must not be merged into
bare-metal tables. It does not register a user carrier or replace PFN sharing tests.

`.github/workflows/clocktime.yml` runs these checks on Ubuntu 22.04/GCC 11.4. CI
artifacts retain the tested Git revision, configs, disassembly, hashes and logs.
The archived Git bundle also permits an offline clone. Hosted artifacts expire;
copy any evidence that must be retained permanently. `VALIDATION.md` records the
review's actual outcomes, not a promise that every future run will pass.

## Separate scalar measurement on the research machine

The new module keeps the existing `control`, `samples`, and page-evidence interfaces.
The original three-API inner `run_batch` source definition is unchanged. This
is not byte identity: changing its caller changes compiler range propagation,
register allocation and layout. Build the same new probe source for reference and
candidate kernels; do not compare a new probe against archived old-probe timings.
New endpoints:

- `scalar_control`: `CPU ITERATIONS ROUNDS WARMUP` (same bounds as the old control).
- `scalar_samples`: the same CSV columns, but five **distinct scalar API labels**.

The scalar labels are `ktime_get`, `ktime_get_raw`, `ktime_get_real`,
`ktime_get_boottime`, and `ktime_get_tai`. The last three measure direct
`ktime_get_with_offset(TK_OFFS_REAL/BOOT/TAI)` calls. Dispatch is once per batch,
not an extra indirect call per time query. The scalar checksum is accumulated from
scalar values; it does not recreate timespec normalization in the benchmark.
Before timing, each scalar value must lie between two corresponding timespec
reads. A wall-clock discontinuity may reject the diagnostic rather than certify
an invalid observation.

Build a **new, coherent READ package** using the existing workflow; it must contain
the new matching reader module. Boot that package normally. Keep original packages
and old campaigns intact. `refresh-tools` cannot substitute a changed kernel or
module into an existing campaign. For a pre-change VKSO comparison, its reference
package must also carry a matching build of this diagnostic module; the original
three-API-only module is not enough. Raw/VKSO comparisons from new packages already
receive the same new probe through `build-images.sh`.

Run from the repository root; substitute the actual package and case:

```sh
D=test/test_gettime/vkso-tests/direct-api
P="$PWD/test/test_gettime/vkso-tests/baremetal/artifacts/direct-normal"
OUT="$HOME/vkso-scalar/candidate-normal-boot1"

# Package-only validation: no tuning, module load or output writes.
python3 "$D/scalar.py" collect --package "$P" --case vkso-normal \
  --label candidate --out "$OUT"

# Matching experimental READ boot only; do not run beside another collector.
sudo python3 "$D/scalar.py" collect --package "$P" --case vkso-normal \
  --label candidate --out "$OUT" --cpu 2 --execute
```

`scalar.py` reuses package validation, strict READ preflight, the existing tuning
context and `/run/vkso-direct-api.lock`. It loads only the package's reader module;
no carrier grafting is needed to measure kernel calls. Cleanup includes module
unload, affinity restore and tuning restore. Failed runs retain `status=FAIL` and
must not enter the summary. `samples.csv`, `scalar.json`, load/unload logs and
`SHA256SUMS` are stored only in the newly requested directory.

Use `--label reference --case raw-normal` for a Raw reference. Each statistical
observation must be from a different boot. Summarize complete diagnostic directories:

```sh
python3 "$D/scalar.py" summarize \
  "$HOME/vkso-scalar/reference-normal-boot1" \
  "$HOME/vkso-scalar/candidate-normal-boot1" \
  --out "$HOME/vkso-scalar/summary.json"
```

The summary rejects duplicate boot IDs, changed samples, mixed kernel/module
identities within a group, or different workloads/hardware/tuning. It computes
means within boots and weights boots equally. It reports descriptive means and
ranges only, not confidence intervals or an equivalence claim. Scalar data use a
separate protocol and never advance `experiment.sh` or enter its formal CSV matrix.

## Performance acceptance boundary

Smaller objects and removed branches are evidence of a real implementation
simplification, not proof of unchanged or improved latency. To qualify a new NUC
image, compare independently booted reference/candidate packages under the existing
controls. Include all three original timespec readers, all five scalar readers,
public ABI/fallback/namespace checks, and the existing READ/UPDATE protocol when
claiming end-to-end non-regression. Do not relabel historical data as measurements
of this change. Do not remove the private fallback, sequence validation, namespace
mapping or output conversion solely to obtain fewer source lines.
