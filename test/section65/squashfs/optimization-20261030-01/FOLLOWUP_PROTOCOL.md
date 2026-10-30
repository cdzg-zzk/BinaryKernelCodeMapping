# Evidence-driven follow-up (user direction updated)

Publication is paused. The currently frozen 30-campaign matrix is allowed to
finish as a version-specific comparison, not as a stopping rule for further
improvement. Its recovery retains the first three completed campaigns and
replaces only the entire interrupted XZ campaign, with unchanged settings.
All 127 partial observations and the original registration are preserved.

No following workload starts until both the recovered serial matrix and its
numerical postprocessing finish. No compilation/profile/memory replay overlaps
formal time. No host settings, credentials, existing user windows or unrelated
processes are changed. Every output is new; failed outputs remain intact.

## Memory and disk boundaries

Parse saved smaps by mapped core, bridge, frontend, dependencies, heap and
unattributed anonymous memory. Preserve both per-VMA sums and rollup snapshots
(rounding can differ). Do not label anonymous memory as bridge allocation
without evidence. Kernel-shared PFN identity is not inferred from PSS labels.

Measure exact file length and filesystem allocated blocks separately for the
carrier/copy, owner/consumer modules, bridge/frontend/translator, existing
dependencies and identical images. Deduplicate inodes inside each deployment
scenario. Report debug data, build/export artifacts and experimental replicas
separately; do not count them as required per-application runtime costs.
The installed generic platform remains separate. Compare both already-prepared
native and user-only premises; unchanged host code is not assumed removed.

Hypothesis M1: much of the residual scale growth comes from libfuse high-level
path/node tables rather than unbounded bridge inode/name retention. A separate
version-locked libfuse 3.10.5 diagnostic reads live table sizes and slab lists
inside its own frontend request, checking counts/layout invariants. Original
scale SIFs, same tar workload, production and instrumented frontend, two full
passes each. Identical archive hashes and successful unmount are gates. These
are untimed direct-FUSE observations, not Apptainer end-to-end equivalence.
The probe's own PSS is reported separately, not silently treated as production.
If M1 is supported, evaluate a compact stable-node/low-level frontend design;
do not evade retention by freeing live kernel references or disabling caching
without measuring lookup/time/lifetime costs.

## Python execution attribution

Hypothesis P1: common decoder execution explains a substantial fraction of the
remaining full Python/XZ difference. Use the existing final-owner controls:
stock, copied-library, copied-retained, copied, VKSO. Retain both libraries
for library/common-retained, equalize loader-path lengths, then separate the
unused-dependency removal and physical backing contrasts. Existing original
Python XZ SIF, compile task and 647-file output oracle; three campaigns, eight
paired randomized blocks, one observation per block/condition (120 total).
This is a separate matrix, never pooled into the 7692-observation confirmation.
Compiler and parser implementation differences remain explicit; no automatic
claim that all library/common differences are caused by adaptation or PGOT.

Hypothesis P2: small fixed-depth bit-tree loop control contributes to the
range-decoder hotspot. Try only unrolling depths 3/6/8, keeping branch-based
rc_bit probability updates, normalization and original native/compiler policy.
The previous mask-based rc_bit candidate reduced branch misses but increased
instructions/time; this candidate does not repeat that transformation.
Differential transitions over all power-of-two limits 2..256 and boundary/random
range states under ASAN/UBSAN, plus existing valid SINGLE/PREALLOC/BCJ streams,
precede measurement. Five randomized diagnostic rounds on the same eight
captured SIF blocks compare word baseline/candidate in SINGLE/PREALLOC and
liblzma. Record text size as well as CPU/wall time. Block benefit alone cannot
promote production; a useful candidate must next pass native/copied/shared
guest/PFN and fair affected-workload comparison under a new version identity.

Results determine subsequent work. Negative results are evidence for choosing
the next mechanism, not a reason to stop improving or to manipulate baselines.
