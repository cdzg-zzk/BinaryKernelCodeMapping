# Final optimization confirmation evidence

Start with [the experiment report](analysis/EXPERIMENT_REPORT.md),
[all paired results](analysis/summary.csv), and
[completion audit](analysis/completion-audit.json).
The manuscript and figures were deliberately not regenerated.

30 campaigns contain 8,172 accepted observations and 541 paired comparisons.
Four identical native campaigns contribute 2,688 observations; all 5,484
remaining observations are new. The interrupted 790-row native campaign is
retained under `support/`, excluded in full, and replaced with the same seed
and conditions. Original queue states and recovery records are both preserved.

`manifest.json` records archive hashes, original locations, analysis-file
hashes and frozen input identities. Each archive contains `MANIFEST.json`
with the original path, member name, byte count and SHA-256 of every file.
The archives contain raw samples, full text execution logs, actual order,
correctness manifests, PFN and resource records, source/config snapshots,
and recovery/cleanup evidence. Repeated correctness manifests are intentionally
retained. The 50 archives occupy approximately 77 MiB compressed.

Verify files and independently replay wall/CPU estimates and campaign-level
intervals from the repository root, without root privileges or server assets:

```sh
python3 test/section65/squashfs/confirmation-20261030-02/verify_bundle.py \
  test/section65/evidence/confirmation-20261030-02/final
```

Kernel binaries, SIF/SquashFS images and large application-output tar files
are not included. Their original server paths and identities remain in run
records; they are needed for new execution, not for the offline statistical
replay. See the [reproduction guide](../../../squashfs/confirmation-20261030-02/README.md)
and [claim coverage](../../../squashfs/confirmation-20261030-02/CLAIM_COVERAGE.md).
Earlier development/failed/rejected candidates are retained separately in
`../development/`, the optimization evidence tree, and the server run root.
