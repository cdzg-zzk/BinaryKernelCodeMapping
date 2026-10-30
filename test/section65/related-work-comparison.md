# Real-application comparison and the duplication motivation

Section 6.5 asks whether an eligible resident filesystem body can support a
real application with useful execution, resource and maintenance behavior.
The Introduction's duplication motivation is tested through actual native
mounts and Apptainer SIF tasks, not inferred from a smaller source file alone.

| Approach | Role in this evaluation | Actual evidence | What the comparison establishes |
| --- | --- | --- | --- |
| SquashFUSE 0.6.2 | Existing specialized user-space SquashFS reader used by the application | Same Apptainer/SIF tasks, default, single-thread and stock-with-translator controls | Complete application performance and helper footprint against an existing implementation |
| LKL, Linux 6.12 | Executed kernel-code rehosting baseline; filesystem-focused build | Existing lklfuse with SIF-offset support; 512 MiB heap selected after sensitivity tests; default and matched positive-cache policies | Measures task-dependent execution and helper costs against a kernel-library configuration; held-out xz loses to matched-cache LKL |
| Rump File Systems | Related-work context for reusing kernel filesystem code with user-space support | Published architecture and motivation; no Rump timing row | Source reuse is an established alternative. LKL supplies the executed Linux/SquashFS rehosting comparison; no measured result is extrapolated to Rump |
| Identical-core copied | Mechanism control, not an external competitor | Same instruction bytes, bridge/frontend/cache policy, separate PFNs; loader/CPU diagnostics | Separates adapter/common-source benefits from the additional physical-backing property |
| VKSO | Resident binary reuse with explicit private service bindings | Real native and Apptainer consumers, nine shared PFNs, independent state/lifetimes, common repair | Actual reuse of the native execution body while supporting the selected application workload |

Primary sources: [SquashFUSE 0.6.2 README](https://raw.githubusercontent.com/vasi/squashfuse/0.6.2/README),
[LKL project and host-library interface](https://github.com/lkl/linux), and
[Rump File Systems, USENIX ATC 2009](https://www.usenix.org/legacy/event/usenix09/tech/full_papers/kantee/kantee_html/index.html).
The evaluated LKL revision is retained in `backend-conditions.md` and the
paper bibliography; the Rump entry follows the publisher's BibTeX.

## Final application argument and limits

1. **Useful, conditional execution:** compared with default SquashFUSE, scans
   improve 4.42–54.58% and include archives 3.30–19.46%. The single-thread
   stock control removes most gzip/lz4 metadata advantage: their archives
   instead cost 1.18%/0.89% more, while xz scan remains 53.59% faster.
   Sequential gzip/lz4 improve about 7%; xz costs 13.10% more than default
   stock. All twelve ordinary tasks beat matched-cache LKL, but the independent
   xz Python compilation takes 16.18% more time than default stock and 6.72%
   more than matched-cache LKL. General application-speed superiority is not
   established.
2. **Private-runtime tradeoff:** small-tree helper PSS is 7.00–7.04 MiB, below
   both stock modes and LKL. At 93,856 visited entries, the retained inode/name
   cache reaches 88.89 MiB, above default/single-thread stock's 28.52/12.91 MiB.
   LKL retains 500.92 MiB in that scale observation. These are helper snapshots,
   not whole-machine savings or minimum memory requirements for any framework.
3. **More executed implementation reuse:** 34 filesystem functions containing
   2,103 original lines, the common LZ4 decoder and 2,604 unchanged XZ algorithm
   lines serve both domains. Nine pages (36 KiB) share native/user backing.
   Native A and real SIF B/C retain private state and independent lifetimes.
   Actual native calls and a real SIF hardware breakpoint reach common XZ.
4. **Common maintenance:** one known upstream repair reaches native, copied
   and shared paths while retaining the adapters in that maintenance experiment.
   Source maintenance also benefits copied and is compatible with LKL/Rump's
   motivation. VKSO adds resident execution-body identity; no comparative
   human-time or competitor-bug study is claimed.

The decoder/dependency control attributes the xz sequential cost primarily to
common-versus-library execution, not physical sharing. Metadata work counts
show fewer decompressed blocks/bytes, but do not assign the entire xz metadata
advantage to a single cause. Versions, FUSE API/cache/thread policies, decoder
choices and hardening differences remain in `backend-conditions.md`.
[The final decisions](squashfs/refinement/RESULTS.md) retain adverse outcomes;
[the claim ledger](claim-verdicts.json) does not silently remove stronger claims.

## Installed-platform business costs

The generic 32 KiB `page_cache_replace` LKM is installed system-wide
infrastructure, excluded from each filesystem subtotal as requested. It is
not charged again per core or process.

Business costs still include the 68 KiB owner and 40 KiB native consumer where
required: 48 KiB above the matched 60 KiB native module. Adding user access to
an already prepared resident service avoids one 36 KiB backing and requests
1,264 bytes of registration metadata. Private runtime state remains included
in the helper observations; allocator/global costs are not silently inferred
from those snapshots. Construction/export/registration takes a median 2.698 s
(range 2.696–6.088 s), summing stages within each campaign before aggregation.
Compilation and module loading are outside that subtotal. Setup is reused
while the owner and registration remain installed; owner/version changes
require fresh deployment. Copied artifact construction is not assumed free.

The final ledger is
`build/squashfs/refined-analysis-01/resource-ledger/resources.json`. These
separate accounting quantities do not form a calibrated whole-machine total.
The preceding 39-campaign publication retains its own numbers and binary
identity in `paper/build/section65-composed-publication-01`.
