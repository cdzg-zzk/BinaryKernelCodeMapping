> This directory documents the historical ISO9660 experiment. Final Section 6.5
> SquashFS matrices and scope are indexed in [STATUS.md](../STATUS.md); these
> earlier results are retained separately and are not pooled with them.

# ISO9660 full-task comparison with LKL

The baseline is the existing `lklfuse` application at LKL commit
`d0f76a77e8c2ca68bd7d96190b8da09040eab072` (Linux 6.12). The task is to mount the
same ISO images, enumerate metadata and read complete file contents, then run
the same GNU find/tar workloads. This does not ask LKL to export an isolated
algorithm. Filesystem source and the lklfuse application are unchanged.

## Source and build

Direct archive downloads returned HTTP 429. The alternative source acquisition
uses the official Linux 6.12 release tarball and the official cross-repository
diff from `torvalds:v6.12` to the pinned LKL commit. `reconstruct.py` verifies the
reconstructed source against the pinned commit's Git tree. Thirteen foreign
tool binaries and HID fuzz seeds omitted by GitHub's textual diff are absent;
their entries are verified from API metadata. These files are not inputs to the
native POSIX lklfuse build. See `build/lkl/acquisition-03.json` for exact scope.

`build.py` uses separate kernel output directories and the existing extracted
libfuse3 headers/libraries. It does not install host packages. Both profiles add
ISO9660, Joliet and zisofs and select UTF-8 as the default NLS charset:

- `default`: the upstream default kernel configuration plus these additions.
- `iso-only`: a filesystem-focused profile that removes other disk filesystems,
  IP protocol stacks, PCI, unused NLS tables and kallsyms. The stock host library
  links socket syscall wrappers, so `CONFIG_NET=y` remains. This profile is not
  described as a mathematically minimal kernel.
- `squash-only`: the same focused profile with ISO disabled and SquashFS/xattrs
  plus gzip, xz, zstd, lz4 and lzo enabled. This profile supports the SIF task in
  `../squashfs/README.md`.

Build failures and configuration corrections are retained in numbered logs;
they are setup observations, not measured developer effort.

## Comparison protocol

`probe.py` checks each selected memory setting against six existing original
kernel fixture cases and the 5,586-file Linux include image. The `mb=` parameter
is configured memory, not RSS. Only settings passing the complete task can enter
formal timing; failed smaller settings remain diagnostic records.

`compare.py` extends the already validated native runner. It retains actual
kernel PFN verification, the optimized shared owner and bridge, original-kernel
correctness references, fresh mounts/processes, warm backing images, CPU
placement and tmpfs output. It records eight randomized blocks with three
mounts per combination. Block medians form paired time ratios and descriptive
bootstrap intervals. Build jobs and QEMU must finish before timing.

The FUSE frontend now retains the inode handle returned at open/opendir, as
lklfuse does, and permits requests without repeated path reconstruction. Both
use a single FUSE service thread, real inode numbers, and zero entry, attribute
and negative-cache timeouts. The copied-core and VKSO paths use the same updated
frontend. Historical native results keep their original frontend binaries;
they must not be silently combined with this campaign.

For each mount, a completed root getattr defines readiness. Startup is recorded
separately from task time. Process RSS/PSS and VmHWM are recorded before/after
the task. VmHWM is the kernel's reported process high-water counter; status RSS
accounting is asynchronous and can lag the precise smaps snapshot (this was
observed in the pilot). Use smaps RSS/PSS for before/after comparisons and label
VmHWM separately, without calling it an exact peak. Neither measures total
machine memory. Report the prepared owner/consumer and
registration-module costs separately, and account for actual shared pages
before adding kernel and user footprints. The optional hold-manager used by
the timing harness is not a required resident service (the completed one-shot
maintenance run proves this).

Linux 5.15.198 versus LKL's 6.12, the private user adapter versus LKL's VFS/cache,
and the different complete runtime support remain real implementation
differences. LKL versus VKSO is an end-to-end comparison. The equal-code
copied/VKSO pair isolates the page-sharing mechanism. Ordinary source reuse,
single-point fixes and existing FUSE application glue are not unique VKSO
advantages.

Source acquisition and scripts being available do not establish runtime
results. Completed run records under `test/evaluation-local/runs/iso9660/`
are the authority for any reported numbers.

## Completed comparisons and name-cache ablation

`lkl-comparison-native-01` retains the initial 49 correctness checks and 672
formal observations. Its user adapter had no positive-name cache, so repeated
path components called the original directory scanner again. A private cache
now retains successful `(parent inode, exact name bytes)` lookups until image
close. It is valid for the selected immutable, single-thread image handle;
misses and aliases still enter the original lookup, and failures are not cached.
Allocation failure falls back to the already obtained successful result.

`lkl-namecache-native-01` adds `vkso-uncached` to the seven earlier variants,
using the same owner and FUSE policies. It passed 56 correctness checks and
collected 768 formal observations (eight blocks, three fresh mounts per cell).
The current bridge is 299 source lines including its optional cache/counters;
the frontend is 197 lines including optional shutdown statistics. Historical
251/169-line counts describe the first prototype, not this final adapter.

The include archive performs 94,199 component lookups, with 88,334 cache hits
and 5,865 entries. Its paired time reduction against the uncached adapter is
67.93%; process RSS rises by about 0.20 MiB. Against focused LKL/8 MiB, archive
time is 42.23% lower but scan time is 16.83% higher. Archive time matches the
identical copied core within the measured interval. This identifies an adapter
bottleneck and a complete-runtime tradeoff; it does not make name caching or
the resulting speedup a unique benefit of sharing kernel pages.

The full four LKL configurations, paired intervals, startup and RSS/PSS values
are in `../lkl-namecache-analysis.json`. Both native campaigns unloaded all test
modules; the final run archive is retained next to its run directory.

## SIF/Apptainer comparison

The stock frontend has no byte-offset option. `sif_frontend.py` preserves it and
builds a separate frontend with 30 added lines: an `offset=` option and wrappers
around the existing synchronous POSIX disk capacity/request callbacks. The
offset must be a multiple of 512 bytes; the actual SIF partition begins at byte
36,864. Filesystem and LKL library source remain unchanged, and the generated
frontend patch is retained under `build-squash-only/sif-frontend`.

Both 16 and 64 MiB configured-memory cases pass the real Apptainer SIF task.
The completed two-campaign comparison, including the Python-to-C argument
translator ablation and the identical-core copied/VKSO controls, is documented
in `../squashfs/README.md` and `../squashfs-application-analysis.json`.
