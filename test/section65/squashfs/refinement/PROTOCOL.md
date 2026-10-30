# Focused Section 6.5 refinement

The 39-campaign composed-LZ4 evaluation and its publication/source freeze remain
valid historical evidence. This extension responds to the user's request for
more substantive reuse, explicit kernel-change accounting, a final-version
native control, and an application-focused paper with bounded diagnostics.
No host boot configuration will be changed.

## Implementation decision before performance sampling

Evaluate a same-owner XZ decoder closure from the matching Linux 5.15.198 tree.
Its stream/LZMA2/BCJ implementation is about 2,600 physical source lines.
Unlike adding dormant functions, both the native xz wrapper and real user SIF
reader must execute the common body. Allocation, CRC and memory services stay
private and explicitly bound. Preserve the source algorithm and supported
BCJ filters. Keep the composed-LZ4 build as a measured predecessor. If
correctness or portability requires unacceptable semantic changes, retain the
failure and report that boundary rather than claiming extra reuse.

Final build selection follows functionality and reuse, not significance.
A codec or dependency change requires new native and application measurements;
old performance samples are never silently reassigned to the new binaries.

## Finite evidence work

1. Kernel-change/build audit: count moved original code, handwritten semantic
   edits, generated bindings, native wrapper changes and build flags separately.
   Inspect machine code for stack canaries, thunks and instrumentation. Explain
   environment dependencies and prototype choices; do not infer protection
   equivalence from functional success. A portable hardening implementation is
   a separate design change unless a bounded feasibility check supports it.
2. Candidate correctness: five-format valid-image checks, matched native output,
   copied/shared byte/PFN identity and private bindings; guest-only malformed
   repair regression. Check actual native XZ calls, shared execution, restoration
   and unload. Recheck simultaneous consumers for a selected final owner.
3. Final native direct control: original, equally optimized normal/relaxed
   references, preceding composed-LZ4 and final candidate in the same campaigns;
   fresh/warm scan/archive over the five-format logical tree. Three campaigns,
   initially eight paired blocks, after a four-block pilot; larger sequential
   archive checks cover xz/lz4. No compilation/QEMU during native timing.
4. Final real-application comparison: three SIF codecs and four existing tasks,
   stock/default and stock/single-thread diagnostic, identical copied/shared,
   competitive LKL settings. Three campaigns with paired randomized blocks.
   Keep deployment costs separate; confirm representative instruction/PFN
   identity and matching output for each run.
5. Independent task: prepare a Python standard-library byte-compilation SIF
   workflow, not used in optimization. Fix its inputs and output validation
   before formal runs. Use actual Apptainer fd/offset execution; gzip/xz cover
   the ordinary and previously adverse codec contexts. Three campaigns of
   eight paired blocks are the initial design; no task replacement for speedup.
6. Bounded attribution: retrieve existing heap-size pilot records; verify the
   actual squashfuse_ll executable and thread policy. One targeted diagnostic
   separates execution choice and unused decoder-library retention for the
   xz/lz4 uncertainty. Existing path/padding investigations stay in the appendix;
   do not restart a search for favorable layouts. Collect work counters for
   the stable xz metadata difference when the existing instrumentation permits.
7. Resource/deployment: retain the installed-platform premise (generic 32 KiB
   module excluded from business costs). Distinguish an already prepared
   native service, preparation from original native, and user-only owner
   deployment. Check metadata-scale retained/peak helper memory with a finite
   scale ladder if the compact-runtime interpretation remains central.
8. Publication: lead with reuse boundary, final native cost, copied/shared
   increment, external application comparisons and maintenance/deployment.
   Move optimization chronology and detailed diagnostics to the appendix.
   Absolute-time table headings identify their estimator explicitly. Preserve
   every prior adverse result and the distinct binary versions.

Each new measurement must resolve one numbered item. Functional pilots,
instrumented diagnostics, formal timing campaigns and resource snapshots are
separate evidence groups. Three campaign means, not all accesses, remain the
primary independent units. No claim of cross-boot or universal equivalence is
added without corresponding evidence.

## Pilot decision and fixed confirmation matrix

The six initial pilots completed: 400 native observations, 336 ordinary
application observations and 48 held-out observations. Each application
backend produced the same 647 Python bytecode outputs. The stock `-s`
diagnostic had one observed helper thread. Native fresh paired log-ratio
standard deviations against optimized normal were approximately 0.3–3.1%.
Application sharing-pair deviations were mostly 0.5–2.7%, but gzip stream
reached 15.4%: one copied execution took 0.460 s versus roughly 0.61–0.64 s
for the other copied/shared observations, with comparable CPU work. Retain
this sample. Its cause is not established from that observation alone.

Before confirmation, fix three campaigns for each cell, one observation per
paired block, and the following block counts: native five-format and
xz/lz4 sequential matrices 8; ordinary applications 12; held-out compilation
8; decoder/dependency diagnostics 4; gzip-stream single-CPU diagnostic 12.
The primary matrix tests effects on the scale of several percent; it does
not promise a 1% sharing bound. The single-CPU diagnostic tests whether
application/helper placement contributes to the noisy two-CPU stream path.
No favorable result or significance threshold determines stopping.

The decoder diagnostic uses the final owner in all cases: library decoding
with both libraries present; common decoding with both libraries retained;
and common decoding with both dependencies removed. This directly separates
execution selection from dependency retention in the final implementation.
It does not retroactively explain every prior composed-LZ4 layout result.

The ordinary application matrix includes stock, stock plus the common
translator, stock single-threaded, copied, VKSO, default-cache LKL512 and
matched-positive-cache LKL512. The held-out matrix omits only the translator
control, whose role is covered by the ordinary matrix. A separate resource
ladder uses 1/4/16 copies of the include tree (5,866/23,464/93,856 entries),
preserving per-file distributions and recording possible SquashFS data
deduplication. It tests retained metadata growth, not multi-client throughput.
