# Application backend conditions

The final XZ-composed confirmation uses the same Apptainer 1.5.5 executable,
real SIF, passed file descriptor, partition offset, container programs,
`runuser`/`taskset` wrapper, tmpfs output, and CPUs 1–2. The image backing cache
is warmed; each sample creates a fresh container and helper. Application
command timing ends at launcher completion and output-pipe EOF; Apptainer's
synchronous cleanup is included. Benchmark result-file deletion, archive
validation, carrier registration and restoration are outside that interval.
Native original/prepared timing
uses CPU 1 and separate fresh/warm filesystem phases.
Application CPU fields are differences in `RUSAGE_CHILDREN` for the completed
command and waited children. They do not include unrelated kernel workers or
establish total-machine CPU consumption.

| Backend | FUSE/frontend and threads | Caching | Decompression |
| --- | --- | --- | --- |
| SquashFUSE | Bundled 0.6.2 low-level frontend; default multithreading; 4–11 helper threads observed in before/after snapshots | Its own metadata/data caches; upstream low-level replies use `DBL_MAX` attribute/entry timeout and preserve file data cache on open | Mapped user libraries |
| SquashFUSE single thread | The same `squashfuse_ll` executable with `-s`; one observed helper thread | Same stock cache policy | Same as stock |
| SquashFUSE + translator | Same binary and behavior, with the same C argument translator used by other backends | Same as stock | Same as stock |
| Copied and VKSO | Same high-level FUSE frontend, `-f -s`, one observed helper thread; same user bridge and core instructions | Same private per-mount inode/name and bounded block/fragment buffers; libfuse positive entry/attribute defaults 1 s, negative timeout 0; inode/name objects retained until unmount; frontend retains one list per open directory | Final owner supplies safe LZ4 and XZ; gzip/zstd/lzo retain user libraries and separate native decoder services. Native XZ uses PREALLOC, user contiguous input/output uses SINGLE mode |
| LKL default | Existing `lklfuse` plus 30-line SIF-offset boundary; one FUSE request thread with LKL internal threads (18 total observed) | Linux 6.12 VFS and filesystem caches; frontend explicitly sets all three FUSE timeouts to 0; 512 MiB heap in confirmation; existing 16/64/256/512 MiB pilots all complete | LKL's built-in Linux implementations |
| LKL matched-positive-cache | Separate frontend changes two timeout assignments; same library, compiler, offset handling and threads | Entry/attribute 1 s and negative 0; 512 MiB heap | Same as default LKL |

The mapped user-library filenames are `libz.so.1.2.11`, `liblzma.so.5.2.5`,
`liblz4.so.1.9.3`, `liblzo2.so.2.0.0`, and `libzstd.so.1.4.8` in the checked
xz baseline formal campaign. Final copied/VKSO binaries remove
liblz4 and liblzma. The bounded diagnostic compares library decoding with both
dependencies, common decoding retaining both, and common decoding removing both.
The other libraries retain
the same versions. Backends use
`libfuse3.so.3.10.5`; subsequent campaign map files remain available for checking.
LKL statically contains its kernel code and maps libfuse, libc and libgcc support.
Configured LKL heap size is not RSS or a promised fully resident allocation.

Actual translated commands and mount options are saved in each backend's
`trace.jsonl`. Common options include `allow_other,ro,uid=...,gid=...`.
The C translator appends one invocation record before exec; this work is inside
the timed lifecycle. The stock-plus-translator control therefore includes both
argument conversion and this tracing cost. Copied/VKSO use identical core
instructions and user support. Their original loader path spellings differed.
Additional controls hardlink those binaries under equal-length paths and
balance padding 0/16 within each campaign; alias inode/byte identities and
actual per-invocation paths are retained. These separately reported controls
cover xz/lz4 scan and stream in the final confirmation. The preceding composed
version has a wider three-codec path/placement matrix, retained as historical
evidence rather than pooled with the final owner.
Whole-backend comparisons include cache algorithms, FUSE API/threads, kernel
version, support-library and build-setting differences. The common core uses
the recorded preparation PIC/instrumentation/mitigation settings; distributed
stock and LKL binaries are not compilation-matched implementations. The
matched-cache diagnostic addresses
one concrete mismatch; it does not make all three filesystem designs identical.

The final prepared filesystem omits the original native stack-canary checks
and external indirect/return thunks. `squash-refine-hardening-02` records the
actual instructions and compile commands. A PIC build-only probe supports
those checks with an explicit native GS-canary convention; runtime binding
of those cross-domain dependencies is not implemented. Configuration has
`CONFIG_FTRACE=n`; this is not an observed loss of active ftrace protection.

A separate final placement diagnostic restricts gzip-stream application/helper
execution to CPU 1 for stock, copied and VKSO. The common outer runuser launcher precedes taskset;
live process snapshots record actual application/helper affinities. This
single-CPU condition is not pooled with the default two-CPU measurements and
does not supply an additional LKL comparison. It addresses broad gzip
wall-time intervals and occasional changes in parallelism with similar
observed CPU work; no original samples are excluded.

Timeout sources: [libfuse 3.10.5 initialization](https://raw.githubusercontent.com/libfuse/libfuse/fuse-3.10.5/lib/fuse.c),
[SquashFUSE 0.6.2 low-level operations](https://raw.githubusercontent.com/vasi/squashfuse/0.6.2/ll.c),
and the retained LKL source at `build/lkl/linux-6.12/tools/lkl/lklfuse.c`.
The external-source descriptions are source-level policy observations; saved
process maps, command traces and thread counts are runtime observations.

Process RSS/PSS/USS omit host image cache, FUSE kernel caches, tmpfs output,
page tables and other kernel allocations. Private-state walks account selected
live requested allocations only. Reported module residency and registration
metadata are separate costs. These measurements do not establish a calibrated
whole-machine net memory saving or a peak process-tree total.

The improved formal runs take both before/after process snapshots before any
PFN or debugger read. Such reads may fault selected pages; they occur only
after the reported memory observations. Historical baseline/pilot snapshots
used the older ordering and are not pooled with improved memory observations.

Business-cost comparisons assume the generic VKSO platform is installed.
Its one-time page_cache_replace module is excluded from business subtotals.
This exclusion does not remove task-specific state, filesystem preparation,
registration metadata, decoder libraries or LKL's required in-process runtime
from the respective measured footprints. All backends use the same host
OS/FUSE substrate. Full platform installation remains separately recorded.
