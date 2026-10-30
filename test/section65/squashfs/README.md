# SquashFS common-core and Apptainer evaluation

Current optimization/confirmation: [confirmation-20261030-02/README.md](confirmation-20261030-02/README.md). The 48-slot version completed its fixed 30-campaign / 8,172-observation matrix and independent replay of 541 comparisons. Delivery is raw evidence and an experiment report; manuscript and figures are deferred. The publication and counts below describe the preserved predecessor.

## Preserved predecessor

The final XZ-composed evaluation is complete: 30 campaigns / 6,540 observations,
five-format and BCJ correctness, guest repair, native and actual SIF decoder
execution, nine shared pages, independent objects/lifetimes, resource scaling
and a compiled Section 6.5. See [STATUS.md](../STATUS.md),
[current reproduction](refinement/README.md), [decisions](refinement/RESULTS.md),
and [claim judgments](../claim-verdicts.json).

Production binaries are in `../build/squashfs/refine-xz-01`; final sources are
frozen in `../build/squashfs/evaluation-refined-02`. XZ composition adds 2,604
unchanged algorithm lines and increases physical sharing to 36 KiB. Native
preparation, private support and resource costs remain explicit. Metadata and
some sequential tasks benefit, but common XZ has adverse sequential/held-out
performance, and the unbounded visited-inode/name cache loses to SquashFUSE at
large metadata populations. These outcomes are retained in the main text.

The generic 32 KiB platform module is excluded from business costs under the
installed-platform premise. Filesystem preparation and per-core/private state
remain included. No human-hour or whole-machine net-memory benefit is inferred.

## Implementation and historical run notes

Details below retain the chronology of early builds and runs and describe
the preceding implementation where explicitly versioned. That baseline uses
`evaluation-fixed-01/build`, with scripts/prose frozen as `evaluation-fixed-06`;
its 34 campaigns remain in `final-analysis-02`. Historical single-campaign
numbers and baseline implementation sizes are not the improved-version
estimates. Those historical implementation/analysis groups remain preserved; STATUS.md
links the final XZ-composed implementation and its independent confirmation.

## Completed native preparation

`prepare.py` starts from the repository's Linux 5.15.198 source and produces a
shared owner (`vkso_sq_core`) and a real native consumer (`vkso_squashfs`, type
`vksosquash`). The latter calls the owner's superblock, inode, directory, block
list and metadata/data-read functions. It retains the existing native page
cache, cache synchronization, BIOs and decompressor implementations.

The current preparation moves 34 functions containing 2,103 original lines.
Two preparation edits precede the separately recorded upstream repair: device-size access in `squashfs_fill_super`
and opaque input-byte/release/error access in `squashfs_read_data`. The other
environment accesses are redirected through 46 service bindings and 10
operation-table fields. These bindings, native helper additions, generated
headers and the user adapter are all part of the adaptation cost; saying
that only two functions need changing would omit this work.

Native input access still uses the original BIO pages and decompressors. The
metadata-header accessor reads two bytes from those pages without introducing
a flattened input buffer on the native path. Dynamic-debug calls are also an
explicit service; native tracing is retained. The compiled common object's
only undefined symbol is its private binding table `sq_support`. This is a
dependency check, not proof that a user adapter is complete.

The owner uses the experimental PIC and instrumentation settings from the ISO
prototype. The build emits the corresponding objtool hardening warnings;
production hardening equivalence is not claimed. Original sources are untouched,
and `build/squashfs/reader-adapted/kernel.patch` and `adaptation.json` record changes.
The current configuration is the native SDK's 5.15.198 configuration, including
direct page output, single decompressor workspace and xattr support.

`squash-native-guest-03` completed ten actual mounts: original built-in SquashFS
and the prepared consumer for gzip, xz, zstd, lz4 and lzo images. It compared
complete pathname, metadata, symlink and file-byte manifests, and checked
hardlink identity, xattr bytes and UID/GID. Fixtures exercise sparse blocks,
fragments, incompressible data and directory indexes. Both test modules unload
successfully. The earlier `squash-native-guest-01` is retained as a harness
failure: `/mnt` was absent before module loading; `parents=True` fixes it.
All these runs use TCG and provide no performance measurements.

## User-domain reader

`user_bridge.c` supplies private inode/name/block caches and binds the shared
format logic to user-domain objects. `posix_io.c` handles file-descriptor input,
partition offsets and ordinary compression libraries. Compression-option and
xattr parsing use the common kernel code; the compression libraries themselves
are not shared kernel instructions. `fuse_frontend.c` exposes the reader as a
read-only, single-threaded filesystem. Its caches currently last until unmount;
there is no general inode/name eviction policy. User and security xattrs are
supported; trusted-namespace xattrs are not exposed by this adapter.

`squash-copied-fuse-01/result.json` records five compression formats plus a
file-descriptor input with a nonzero partition offset. All six mounts matched
the native oracle's 412 entries and passed 22,032 random/boundary reads in total,
hardlink and xattr checks, read-only rejection and execution of GNU tar. This
proves a copied-core FUSE reader, not Apptainer execution or page sharing.

The first shared run failed in the test harness before starting FUSE. The second
reached FUSE but found a real exporter defect: KRG omitted local string symbols,
leaving the string page referenced by directory enumeration unmapped. The
exporter now collects referenced readonly sections from module relocations.
`make_dll/tests/test_module_ro_closure.py` covers a local string on a second page,
a private-data pointer with an addend, and exclusion of an unrelated section.
Both failed runs remain available as `squash-export-01` and `squash-export-02`.

`squash-export-03` passed shared gzip/lz4/lzo mounts before exposing a second
exporter defect: the private image did not account for Linux's page-aligned
ro-after-init group (`__jump_table`), placing the binding table over ELF dynamic
symbols. The crash happened during `dlsym`, before xz image initialization.
`compute_core_layout()` now preserves this group and checks resolved symbols
against the inferred runtime layout. A new layout regression and all 24 exporter
tests pass. The corrected materialized image passed 100 xz probes and the full
six-mount check in `squash-materialized-fuse-01`.

`squash-export-04` completed the physical-sharing verification. Both actual VKSO
and the materialized control passed six mounts and 22,032 boundary/random reads
each. For every compressor, all six mapped pages (four text, two readonly;
24 KiB total) matched the kernel PFNs in the VKSO process, while none matched in
the copied control. All 46 service pointers targeted user addresses. Five native
mounts before and five after sharing matched the original native oracle. The
registration process had already exited; explicit restore recovered the original
carrier bytes and all four modules unloaded. These are TCG functional results.

## Reproduction

From the repository root, using the existing native SDK and initramfs:

```sh
python3 test/section65/squashfs/prepare.py --output test/section65/build/squashfs/reader-adapted --build
python3 test/section65/squashfs/fixtures.py --output /path/to/new-fixtures
python3 test/section65/squashfs/preflight.py \
  --build test/section65/build/squashfs/reader-adapted \
  --fixtures /path/to/new-fixtures \
  --output test/evaluation-local/runs/iso9660/squash-native-guest-new
```

The guest boots the exact raw-normal 5.15.198 kernel image. No SquashFS test
module has been loaded on the host. Output directories must be new; failed
runs are preserved.

## Actual Apptainer task

`apptainer_preflight.py` builds a SIF containing GNU tar and the Linux 5.15.198
include tree, then runs the unmodified archive tool inside Apptainer 1.5.5.
The official Ubuntu Jammy package is extracted locally under
`build/squashfs/apptainer/jammy`; its stock backend is SquashFUSE 0.6.2.
`libtalloc2` and `libprotobuf-c1` are extracted under `apptainer/runtime` for the
bundled proot build helper, without host package installation.

`apptainer_helper.c` translates Apptainer's existing helper arguments. The
application and Apptainer source are unchanged. A per-run configuration selects
the reader helper ahead of the bundled backend. The first implementation used
Python and immediately execed the C frontend. Its measured startup cost motivated
the current C translator, also followed by exec. `apptainer_helper.py` and
`--translator python` retain that ablation; all final timing includes the C
translator. The reader, I/O bridge, FUSE frontend and translator contain
369 + 87 + 221 + 96 = 773 source lines, excluding the kernel preparation,
generator and experimental harness.

`squash-apptainer-copied-02` passed stock/reader comparison over 5,866 archive
entries. The actual helper received `/proc/self/fd/3`, partition offset 36,864,
`allow_other,ro,uid=1000,gid=1000`. This is a real SIF partition and container
execution, beyond the earlier synthetic offset fixture.

`squash-apptainer-shared-02` repeated the task with a registered carrier on the
5.15.198 host. Apptainer ran as the ordinary user in its unprivileged mode;
registration and PFN observation ran as root in a private mount namespace. All
six code/readonly pages matched native PFNs during the mounted application,
and 46 bindings pointed to user addresses. The container archives matched the
stock backend. The original native filesystem and prepared consumer also read
all 6,182 SIF root entries identically before sharing, and the prepared consumer
did so again after application execution. The carrier was restored and all
modules unloaded. The earlier `shared-01` completed its application but failed
the observer's log lookup: Apptainer consumes helper output. Observation now
locates the binding table from ELF symbols and process mappings.

```sh
python3 test/section65/squashfs/apptainer_preflight.py --output /path/to/new-copy-run
sudo unshare --mount --propagation private \
  python3 test/section65/squashfs/apptainer_shared.py \
  --user zzk --image /path/to/new-copy-run/headers.sif --output /path/to/new-shared-run
```

The copied run `01` failed before building the SIF because proot's runtime
dependencies were missing; the successful `02` supplies them locally.

## Initial native preparation cost

`squash-native-cost-01` contains 96 checked hardware observations from eight
paired blocks on the same gzip SIF. Each workload gets a fresh mount, followed
by two warm traversals; variant order is randomized within each block. The
compressed image is cached, clients run on CPU 1, and actual archive bytes go
to tmpfs. Every output digest agrees between original/prepared paths. This is
one image and one boot, not a cross-machine or cross-compressor result.

| Task | Paired prepared/original time change | Block-bootstrap 95% interval |
|---|---:|---:|
| Archive, fresh mount | +0.29% | +0.02% to +0.61% |
| Archive, warm | +0.89% | +0.17% to +2.14% |
| Directory scan, fresh mount | +4.28% | +2.60% to +5.89% |
| Directory scan, warm | +0.80% | −3.49% to +6.87% |

The fresh directory scan has a measurable preparation cost. Warm-scan variation
does not yet resolve a small difference. These measurements concern native
kernel preparation, not VKSO versus SquashFUSE application speed.

```sh
sudo unshare --mount --propagation private \
  python3 test/section65/squashfs/native_cost.py \
  --image /path/to/headers.sif --offset 36864 --output /path/to/new-native-run
```

## Remaining implementation

The same core's copied and shared FUSE paths now pass full reads and physical
page checks. Native overhead and aligned application performance have hardware
measurements. A concrete maintenance experiment remains outstanding.

The exercised Apptainer path covers file-descriptor input, a SIF partition
offset, read-only permissions, UID/GID handling, mount readiness/cleanup and
container program execution. It does not cover its privileged preopened-FUSE-fd
mode, writable filesystem operations, or the whole Apptainer feature set.
The completed comparison includes existing SquashFUSE, LKL's filesystem path,
original/prepared native drivers and identical-core copied/VKSO controls.
All added code/state and a concrete maintenance case must be accounted for
before claiming lower development effort or deployment cost.

## Completed application comparison

`squash-apptainer-comparison-01` and `02` each contain eight randomized blocks,
two executions per cell, six backends and two workloads (192 observations each).
All backends passed the 5,866-entry archive comparison before timing; every timed
archive was checked again outside the measured interval. Compressed image pages
are warm, every sample starts a fresh container/mount, clients and helpers share
CPUs 1 and 2, and outputs go to tmpfs. Timing includes startup, command execution,
cleanup and the common runuser/taskset launcher. Resource snapshots are separate
untimed executions. Both campaigns verified copied/shared PFNs and restored the
carrier and unloaded modules afterward.

The first campaign includes the Python translator. Wrapping stock SquashFUSE in
that same translator increased archive lifecycle time by 12.12%; VKSO was 7.38%
slower than unwrapped stock. The second campaign replaces only that translator
with C and retains a wrapped-stock control. This diagnoses integration overhead;
the initial result is retained rather than silently replaced.

Final second-campaign medians and one post-archive helper RSS snapshot per backend:

| Backend | Empty task lifecycle | Archive lifecycle | Helper RSS after archive |
|---|---:|---:|---:|
| Stock SquashFUSE 0.6.2 | 142.33 ms | 961.93 ms | 16.10 MiB |
| Stock with C translator | 142.14 ms | 962.41 ms | 16.22 MiB |
| Identical-core copy | 146.91 ms | 919.83 ms | 9.13 MiB |
| VKSO | 147.18 ms | 914.66 ms | 9.16 MiB |
| Focused LKL, 16 MiB configured | 238.54 ms | 3450.88 ms | 25.09 MiB |
| Focused LKL, 64 MiB configured | 219.22 ms | 2388.55 ms | 62.12 MiB |

Paired block ratios, rather than ratios of these displayed medians, give VKSO
archive changes of −4.80% versus stock (95% interval −5.05% to −4.53%), −73.15%
versus LKL/16 and −61.90% versus LKL/64. Empty-task startup is +2.91% versus stock
(+1.20% to +4.31%). Against identical copied code, archive time is −0.54%
(−0.90% to −0.20%) and startup +0.26% (−0.83% to +1.33%). The small copied/shared
difference should not be confused with the complete-runtime advantage over LKL.

`lkl/build.py --profile squash-only` retains the pinned Linux 6.12 LKL library and
filesystem sources. `lkl/sif_frontend.py` adds 30 lines to a separate copy of its
existing frontend for sector-aligned SIF offsets through the provided POSIX disk
callbacks. Both memory settings complete the same SIF task. This baseline does
not ask LKL to export an isolated algorithm. Its VFS/cache and FUSE policies still
differ from the lightweight adapter; only copied/VKSO isolates page sharing.

The memory numbers describe helper processes, not net machine memory or exact
peaks. Kernel preparation/registration costs remain separate. There are no
measured developer hours, and VKSO's first-use adaptation is larger than LKL's
small frontend extension. The supported advantages here are a smaller user
runtime and competitive full-task execution while sharing actual kernel pages;
the data do not establish lower first-use development cost.

`analyze_application.py` audits both campaigns and writes
`../squashfs-application-analysis.json`. Reproduce the final comparison with:

```sh
python3 test/section65/lkl/build.py --profile squash-only
python3 test/section65/lkl/sif_frontend.py
python3 test/section65/squashfs/build_user.py
sudo unshare --mount --propagation private \
  python3 test/section65/squashfs/apptainer_shared.py --user zzk --benchmark \
  --lkl test/section65/build/lkl/build-squash-only/sif-frontend/lklfuse \
  --image /path/to/headers.sif --output /path/to/new-comparison
```

An inspected maintenance candidate is upstream
[`e300eb500292`](https://github.com/torvalds/linux/commit/e300eb5002925b29be803d2661af07266cfa267e),
which rejects negative block-copy offsets in the shared `squashfs_copy_data`.
The pinned kernel lacks this change. It is not yet a completed maintenance
experiment, and native zero-fill versus user short-copy error semantics must
be checked rather than assumed identical.

## Completed negative-offset maintenance matrix

`squash-maintenance-02` now completes old/fixed × native/copied/shared on
the controlled valid and malformed fixture. The original run remains unchanged.
Old copied and shared daemons both terminate with SIGSEGV; their clients observe
ENOTCONN (107). The old native consumer subsequently panics with RIP in
`squashfs_copy_data`. Successful valid-input controls, daemon signals, target
function and kernel panic jointly identify the expected defect.

With upstream commit `e300eb5002925b29be803d2661af07266cfa267e` backported,
all three consumers return EIO (5) for the malformed read. Both user daemons
survive until orderly unmount. This follows the actual application observations:
the common function returns zero copied bytes; native `squashfs_fill_page` clears
the remainder and marks a page error when copied bytes differ from the request,
while the user bridge rejects the short copy. Internal zero filling therefore
does not imply a successful zero-filled application read in this case.

The same-version unadapted filesystem with only registration renaming and the
same upstream patch independently returns EIO, preserves the valid payload,
and passes five native format regressions (`squash-maintenance-reference-01`).
Reproduce with `maintenance_reference.py --maintenance <completed-maintenance>
--output <new-directory>`. Both abnormal-image experiments run only in TCG.

Fixed copied and shared paths each pass six mounted cases and 22,032
random/boundary reads; five prepared-native format manifests also pass. Shared
PFNs match the kernel and copied PFNs do not. Carrier restoration and all
module unloads complete. The owner changes, while bridge and frontend hashes
remain identical. `upstream-backport.patch`, build logs, owner hashes and
per-case evidence reside in the new maintenance directory. This requires
rebuilding and deploying the owner/consumer, exporting and registering a new
carrier, and starting new consumers; it does not demonstrate live updating.

Final-version evaluation is tracked in [the research protocol](../research-protocol.md).
`evaluation-fixed-01` freezes the fixed binaries, generated source, configuration,
compiler identity and experiment scripts. Further runner changes require an
updated manifest before formal sampling. Old unpatched timing remains historical
until corresponding final-version measurements are collected.
