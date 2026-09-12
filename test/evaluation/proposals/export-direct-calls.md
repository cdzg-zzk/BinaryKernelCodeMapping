# Shared executable references and Shim binding: unapplied proposal

Status: proposal only, 2026-09-12. The actual exporter and checker have not been edited. No patched tool has been used for a campaign or guest run. The patch implements rejection of unsupported bindings; it does not make the pending LZ4 CLI matrix pass.

## Observed failure and active source path

`vkso` invokes `run_function_checks` before `build_PIC_so.py` (`vkso:544–564`, `568–615`). It does not invoke `build_LKM_so.py`.

1. `functions_checker.py:669–678` treats a PC-relative executable relocation to an undefined symbol listed in `self.shims` as successful Shim interception. It does not require any writable binding location that could redirect that reference.
2. `build_PIC_so.py:1103–1129` traverses KRG with Shim stop names, marks those nodes undefined imports, and stops their native dependencies. `build_shared_object:1853–1866` selects this policy before examining the owner object.
3. The later owner processing emits dynamic relocations for the private `.data` image (`1938–2003`). It does not redirect unchanged direct calls in shared executable pages. An undefined dynamic symbol alone does not alter an already relocated `call rel32` instruction.
4. Consequently, both checks pass and the current builder emits a DSO with module code pages and imported helper names, while a direct helper target has no mapped destination.

The full CLI failure was reproduced with a freshly rebuilt, unchanged owner using exact `5.15.0-119-generic` headers. In attempt06, the kernel call at `0xffffffffc0009e78` targets `memset` at `0xffffffff816bb8a0`, a displacement of `-1049945565`. Applying that displacement at the user call `0x7ffff7d87e78` predicts `0x7fffb94398a0`. GDB observed exactly this RIP and showed no mapping there. The call arguments were `rsi=0`, `rdx=16416`. Execution had not entered any Shim/libc helper. Four active page aliases and four restored-away PFNs were verified independently.

Evidence: `../results/lz4-cli-qemu-20260912-attempt06/diagnosis.json`, `evidence/validation/full-cli-gdb-diagnostic.log`, and `owner-build-evidence/` in that attempt. Original and fresh compression function bytes match; the entire old/fresh owner binaries do not, because the decompressor differs. The fresh-owner runtime failure establishes the current source result.

## Proposed rejection patch

`export-direct-calls.patch` changes two core files, without applying either change:

- The checker records a PC-relative executable reference to a configured undefined Shim as an unsupported binding and returns `FAIL`. It no longer reports successful interception at that site. Existing explicit private data-slot analysis and built-in thunk handling are not rewritten by this patch.
- The active PIC builder checks the finally selected shared owner functions before writing the DSO, page map, or dependency declaration. It rejects executable relocations to imported Shim symbols. It also disassembles selected functions to catch resolved local direct branches to locally defined symbols that were classified as Shim imports and therefore have no relocation record.
- The guard excludes unselected functions, including other functions resident on the same source page. It excludes private synthetic code and does not mistake a supported `.data` pointer slot for a direct executable binding. Unbounded or incompletely decoded selected bodies are rejected when a Shim import requires this check.
- Ordinary dynamic imports are not converted to synthetic trampolines, shared instruction bytes are not rewritten, and native helper pages are not silently added. The diagnostic identifies the function, offset, symbol, and relocation kind.

This is a concrete change from a falsely usable export to an explicit unsupported-method result. It is not a complete native-closure implementation. Applying it will make the present full LZ4 command stop before registration until its dependency-binding method is corrected and validated.

## Relation to `build_LKM_so.py`

`build_LKM_so.py:139–168` scans executable relocations across the owner, forms `exec_shim_conflicts`, and removes those names from `shim_targets`. It then follows the corresponding native dependencies. This recognizes the direct-call constraint, but simply transplanting it into the active PIC path is insufficient:

- Its scan covers all core executable sections, including functions outside a selected API closure.
- It retains hardcoded `base_stop_names` alongside computed stops. Removing a name from Shim classification does not itself prove an untruncated, usable native closure.
- It includes all owner text/rodata ranges (`:242–243`) and lacks a final resident-instruction control-target check.
- The independent checker would still need to analyze the same effective native dependencies; its current Shim policy can otherwise stop at a helper the exporter retained natively.

The proposal therefore reuses the constraint, not this builder's broad selection policy. No switch to `build_LKM_so.py` or historical page maps is proposed as a shortcut.

## Requirements for completing the binding method

A subsequent implementation should choose and record an actual binding mechanism for each selected dependency edge:

1. A direct reference in unchanged shared code retains its native target and requires the complete reachable native control closure, with relative layout preserved and all dependencies checked under that same policy.
2. A domain-specific replacement uses an explicit private writable slot with a supported relocation and ABI contract. The emitted dynamic relocation must name that slot; a Shim name in a report is insufficient.
3. The existing built-in thunk mechanism is represented as synthetic code at a documented translated target. It remains distinct from ordinary dynamic Shim imports.
4. Before execution, walk the final resident control flow from the actual exported entries. For every reachable direct branch, establish the translated target, its intended code identity, and coverage by the final mapping. Continue through newly discovered native helpers. Merely finding the target somewhere within a copied source page does not establish its intended binding.
5. Treat unresolved control transfers, module identities, or runtime-patched targets as incomplete. Indirect targets require the explicit dependency/callback contract and its binding evidence.

The native-retention route requires more work than the rejection patch. Any owner adaptation or foundational exporter change should be reviewed separately before use. No LZ4-specific names or fixed addresses belong in the general correction.

## Existing tools cannot fully validate native runtime closure

The current KRG reads ELF bytes and then substitutes runtime addresses. Its persisted CSR edges have no call-site or binding-kind provenance. `krg.cpp:906–1068` adds immediate CALL/JMP and some memory-indirect edges; this is not a general final resident-code control-flow proof. The save path (`1110–1214`) keeps unsafe dependency leaves and applies live section bases, rather than decoding post-load instruction bytes.

The Python checker also decodes ELF input. Its kallsyms-derived addresses are presentation data. PFN observation proves physical aliasing, not branch completeness, and a page map cannot show which helper implementation executed. Runtime alternatives, static calls, tracing/return patching, and unresolved indirect transfers therefore remain outside a complete validation guarantee. The proposed guard likewise does not certify built-in-vmlinux exports, native helper internals, cross-module native code, or final runtime patching.

## Validation performed

`python3 test/evaluation/proposals/export-direct-calls-validate.py` applies the patch only in a fresh temporary directory, imports those isolated copies, and verifies:

- 10 assembled-machine-code binding fixtures: direct call, tail jump, PC-relative address, valid private data slot, an unselected direct call on the same text page, a local branch without relocation, zero-size/missing body, incomplete decoding, and built-in/native distinctions.
- 4 original/proposed checker invocations: direct Shim call changes from PASS to FAIL; private data-slot fixture remains PASS. This is a binding-regression check, not certification of that fixture's complete runtime ABI.
- An offline replay of the fresh LZ4 owner and actual attempt06 live-guest KRG. The original builder emits a DSO; the isolated proposed builder rejects the four executable binding sites before any DSO, page map, or module dependency file is emitted.
- Actual core source hashes remain unchanged; `git apply --check` succeeds.

Results are in `export-direct-calls-validation.json`; the original core identities are recorded in `export-direct-calls-source-identities.json`. No guest or performance experiment used the proposed tools.

## Historical memory-helper claim

The current manuscript says kernel-backed and same-source no-SIMD use the same test-local REP memory helpers. Existing historical evidence does not establish that identity:

- `test/test_lz4/results/metadata.txt` labels kernel helpers as Shim imports and separately labels no-SIMD helpers as test-local scalar helpers.
- `kernel-page-mappings.txt` includes kernel text pages at `0xffffffff91ebb000`, `0xffffffff925cb000`, and `0xffffffff92802000`. The companion resolved-symbol file places `memset`, `memset_orig`, `memmove`, `memcpy`, `memcpy_orig`, and a return thunk in those pages, although some are also labelled Shim imports.
- `kernel-relocations.txt` contains nine private-data relocations and no helper call-slot relocations. `DT_NEEDED: libshim.so` therefore does not prove that these direct memory-helper calls were redirected.
- `simd-audit.md` audits the four ordinary DSOs; it does not audit the actual kernel-backed helper execution. `correctness-trace.log` names the selected algorithm backend, not the executed helper entry.

These records contradict treating the declared import labels as proof of identical helper binding. They support the presence of native helper pages, but do not by themselves prove the exact helper body executed historically. The old live resident instruction bytes and helper IP traces are absent, and the archived old owner binary hash differs from the currently available owner. Preserve historical timing values as observations, remove the unsupported helper-identity claim, and avoid attributing their ratio solely to execution placement until actual helper-path identity is measured.
