# Original Layer-3 audit (before benchmark changes)

Scope: only the four fixed-input Layer-3 PGOT workloads. The September export
campaign is unrelated. `historical-hashes.json` records all 323 historical
files before this revision; `prechange/` preserves benchmark sources, build
scripts and newly reconstructed objdump output from all eight archived KOs.

## Actual experiment

Origin and adapted copies execute inside the same kernel module. SHA transforms
a fixed 64-byte block and accumulates state; BCH encodes 512 bytes with
m=13,t=8,swap_bits=true (ECC clearing is inside timing); zlib resets its stream,
sets up buffers and compresses the fixed 342-byte text with level 3/Z_FINISH;
Zstd begins its context and decodes the fixed 155-byte frame. Allocation and
major initialization are outside timing. BCH/zlib/Zstd compare variant outputs
before timing. **SHA currently lacks an explicit output comparison**, despite
the broader manuscript's correctness description; this must be added outside
the timer in the confirmatory build.

SHA/BCH are explicitly assembled C benchmark implementations, including
noinline/noipa and compiler barriers, rather than unmodified distribution
objects. SHA materializes the Origin constant-table address in a register and
uses the same compiler barrier as PGOT. BCH similarly constrains table setup.
zlib/Zstd copy and rewrite Linux source through generators. Memory builtins are
disabled for zlib/Zstd; selected attributes suppress tracing and align bodies.
These are adaptation comparisons under these compiler conditions.

All archived runs pin CPU 2 and disable preemption and local IRQs inside each
sample. LFENCE/RDTSCP delimit the whole batch; values labelled cycles are TSC
ticks, not PMU core cycles. Each ABBA/BAAB round averages its two Origin and two
variant batches, normalizes by calls, and retains one paired record. Three
module-load runs each contribute 31 such records at every scanned batch size.
The batch does not reset state identically across algorithms: SHA evolves its
state, BCH clears ECC, zlib resets the stream, Zstd begins the context.

## Binary checks performed before changing sources

Fresh `objdump -dr --no-show-raw-insn` output is saved in `prechange/`.
SHA's transform has no indirect calls in either variant/build; Data-PGOT has
the `pgot_k_table` relocation/load, Origin has the direct table reference.
BCH `swap_bits_data_pgot/all_pgot` contain the table slot load. In Func/All,
load_ecc8 and store_ecc8 each have one memcpy slot call and bch_encode has two.
The no-retpoline objects contain indirect calls; corresponding retpoline
objects contain inline call/pause/lfence/stack-target/ret sequences. The
Origin/Data memory helper forms remain direct.

zlib's Origin already contains an indirect configuration-table dispatch;
its retpoline build already protects that dispatch. Func/All add memory
helper bindings; internal algorithm helpers remain as generated direct calls.
Zstd's top-level entry calls lower copied routines directly; memory slot calls
are in those lower routines. Looking only at decompressDCtx would miss them.
Full source-site and object-site inventories are generated separately, with
function names and instruction offsets, not inferred dynamic call counts.

## Discrepancies

1. `select_layer3_stable_rows.py` ranks observed results by labels derived from
   delta/IQR, then by IQR/absolute(delta). This selects using the measured effect
   and may favor large absolute deltas, even with equal measurement precision.
   Different variants/builds consequently use different batches.
2. `paper_table_selected.csv` and `stability_diagnosis.md` disagree with the
   current per-routine raw CSVs and per-routine summaries. For example, the
   selected SHA no-retpoline Origin is 1314.389, while the archived raw scan
   at its selected batch reconstructs a different value. Preserve the published
   selected numbers as historical reports, but do not fabricate outer-run
   observations for them. Reconstruct authoritative results from raw CSVs;
   separately apply historical batch choices to available raw data for a
   traceable selection-only comparison.
3. Some files named `final_layer3_*` are also a different summary from the
   selected table. File names do not establish provenance.
4. The archive has no separate timestamp-pair calibration. Measure it on the
   current same-machine/kernel environment with exactly the timestamp sequence;
   label this retrospective calibration, not a July measurement.
5. IQR/absolute(delta) labels are heuristics, not significance/equivalence
   tests. IQR greater than absolute(delta) does not prove a zero effect.
6. The three outer runs, not 93 inner pairs, are the repeat units. The revised
   analysis must expose run medians and their range. Formal timing will use
   eight module loads per build and 15 balanced pairs per comparison.

The fixed workload and timed computation will be retained. New correctness
markers, SHA equality validation and optional separately compiled diagnostics
must execute outside the formal timed path. Historical files remain untouched.
