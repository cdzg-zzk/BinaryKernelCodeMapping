# Section 6.5: filesystem reuse evidence

The final XZ-composed evaluation is complete: 30 campaigns / 6,540 timed
observations, independent replay of 403 comparisons, final-core functional and
maintenance checks, actual shared decoder execution, private-state/PFN evidence,
resource scaling and a compiled Section 6.5. Start at [STATUS.md](STATUS.md).

The result establishes useful conditional application reuse, with explicit
xz sequential/held-out costs and large-tree private-cache growth. It does not
claim universal speed, compactness, developer-time or whole-machine savings.

- [Paper PDF](../../paper/filesystem-section-preview.pdf)
- [Claim-to-experiment map](claim-experiment-map.md) and [claim judgments](claim-verdicts.json)
- [Current reproduction and coverage](squashfs/refinement/README.md)
- [Analysis and cost/resource ledgers](build/squashfs/refined-analysis-01/)
- [Completion verification](final-evidence.json)

The preceding 39-campaign and earlier 34-campaign implementations remain
separate; their publication snapshots and raw records are linked from STATUS.

## Historical ISO9660 investigation

The following records retain their original versions and exploratory scope.
Their timings are not pooled into the final SquashFS campaign estimates.

The follow-up [filesystem/FUSE feasibility assessment](fuse-assessment.md)
now verifies actual FUSE mounts and GDB hardware-breakpoint debugging of the
kernel-shared instruction pages. See `fuse-export-01` for the mounted-task,
physical-sharing, debugging, and subsequent kernel-regression evidence.
At that historical stage, SquashFS integration was unverified. The final
SquashFS experiments below supersede that status; developer-time savings remain
unestablished.

This work tests whether a complete ISO9660 image-access task can use VKSO at
reasonable adaptation and deployment cost. This initial investigation preceded the final paper experiments.
The decision requires actual implementation and execution evidence, not just
the existence of comparable filesystem projects.

The initial feasibility investigation established the selected read-only image
task. The current reassessment accepts one-time kernel preparation as a premise
and separately evaluates native-path effects, first user-domain integration,
additional application integration, and subsequent maintenance. See the updated
[assessment](fuse-assessment.md) and the generated
[evidence ledger](reassessment-evidence.json). Native measurements now ran on
the benchmark host with the supplied sudo authorization. The initial preparation
regressed the large directory scan by 21.60%; restoring constant-size memory
operation optimization and preserving private helpers reduced the measured
increment to 2.47% (tar: 0.99%).
See [native-analysis.json](native-analysis.json) for audited, paired results and
their intervals. These are exploratory preparation measurements, with compiler
limitations described in [native/README.md](native/README.md).

The completed [matched LKL comparison](lkl/README.md) now includes a private
positive-name cache and an uncached ablation: 56 correctness checks and 768
formal observations. On the 5,586-file include image, VKSO/FUSE archive time is
42.23% lower than filesystem-focused LKL with an 8 MiB heap setting; directory
scan time is 16.83% higher. The archive process RSS snapshots are 7.34 versus
17.11 MiB, and mount readiness about 7 versus 100 ms. These compare complete
implementations; equal-code copied/FUSE is essentially tied for archive time.
See [audited cache results](lkl-namecache-analysis.json); the earlier slower
uncached results remain in [lkl-analysis.json](lkl-analysis.json). This does not
establish lower first integration effort or whole-deployment net memory savings.

The current functional preflight also runs the benchmark's actual 5.15.198 boot
image in TCG: five paths pass 35 correctness checks, including a Linux include
tree, and execute the complete GNU find/tar collection and unload sequence.
These timings validate the runner only. The packet is under
`test/evaluation-local/packages/iso9660-native-20261029`.

The manager's `--hold` process is optional. The completed
`maintenance-oneshot-01` run verifies registration followed by process exit,
shared FUSE reads and hardware-breakpoint debugging, then explicit restore and
module unloading. The same run reproduces a real long-Joliet defect in the
original driver/copy and checks the backported repair in the kernel, copied
FUSE and shared FUSE paths, using unchanged user adapters. This is functional
evidence, not a measurement of debugging time or live code replacement. Neither
the 20 KiB physical sharing result nor optional helper RSS alone is a complete
deployment-memory comparison.

The required task is image open, pathname lookup, directory enumeration,
metadata and symlink access, and file reads spanning blocks. Real images and
their extensions must work; an isolated conversion or extent routine does not
satisfy this task. The shared instructions must also serve an actual kernel
filesystem path, not only an otherwise unused owner module.

Validation and comparison requirements:

1. Preserve a source-identified Linux implementation and record unadapted export
   diagnostics before making the necessary source/build changes.
2. Validate complete results against independent image tools and kernel mounts,
   including the selected images' Rock Ridge/Joliet and multi-extent behavior.
3. Run the adapted kernel filesystem and user path; establish the common code's
   physical backing and check domain-private state and registration lifecycle.
4. Compare with the same adapted code in a copied user library and an ordinary
   ISO9660 library. Investigate matched LKL/rump baselines for the same full task.
5. Account for the whole adaptation and runtime support. Separate preexisting
   kernel residency from modules loaded solely for this task. Do not infer
   memory savings from ordinary DSO code being mapped in several processes.
6. Decide whether the functional scope, external comparisons, costs, and actual
   deployment motivation justify a Section 6.5 case. An unsuccessful export is
   diagnostic evidence, not by itself a final impossibility result.

Sources and test logic belong here; local build products are under `build/`.
Raw runs go under `test/evaluation-local/runs/iso9660/`. Existing paper results
and host boot configuration are not part of this development workspace.

The current host lacks `/dev/kvm`. Private TCG guests validate new module
variants before authorized native execution; their timings are not performance
evidence. The host supports ordinary FUSE mounts, and native campaigns also
verify shared kernel-page PFNs. QEMU and compiler jobs are stopped during
native timing. Supplied sudo credentials are not stored in scripts or packages.

Final functional evidence is under
`test/evaluation-local/runs/iso9660/export-03/evidence/`. The source and ABI
versions are deliberately recorded separately in `upstream/provenance.json`
and `build/raw/build.json`.

To reproduce with the existing local kernel119/initrd assets and generated
images, from the repository root:

```sh
python3 test/section65/prepare.py
python3 test/section65/adapt.py
python3 test/section65/build_user.py
python3 test/section65/reference_qemu.py --export --timeout 1200 \
  --output test/evaluation-local/runs/iso9660/export-new
python3 test/section65/costs.py \
  --output test/evaluation-local/runs/iso9660/costs-new.json
```

Use a new output path: existing runs are not overwritten. `--export` runs in a
private TCG guest, loads the two filesystem modules and the existing project
registration/observation modules, checks actual kernel mounts, constructs and
registers the carrier, exercises shared/copied/concurrent readers, verifies
restoration, and unloads all test modules. It does not load modules on the host.

`fixtures.py`, `check_reference.py`, and `check_libarchive.py` retain fixture
generation and independent-library checks. They are functionality tools, not
performance harnesses. The reference oracle in `reference-01` is required by
the export runner; run `reference_qemu.py` without `--export` to regenerate it
in a fresh checkout before the export step.

