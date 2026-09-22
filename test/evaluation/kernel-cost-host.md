# Same-deployment kernel cost collection

See [section 6.3 methods](../section63/methods.md) for the current baselines,
workloads and timing boundaries, and [current results](../section63/README.md)
for raw data, complete paired summaries and reproduction commands.

`../section63/scripts/campaign.py` prepares controls from the newly
built owner, then invokes `kernel_cost_host.py collect` after the user workload
while that same owner remains registered. The collector checks its build ID
and registration reference; it does not reload the owner between domains.

The kernel matrix covers all twelve Silesia files, BCH t=4/8 and every configured
error count, and the three complete XZ streams. Each backend uses eleven rounds.
`formal_kernel_audit.py` reconstructs inputs, output checks, timing rows, API
providers, compiler comparisons and registration release from retained records.
PFN observations have their own evidence populations.

LZ4 application/setup results are maintained [separately](results/application-setup/README.md).
Do not use collector wall time as setup cost or pool those command measurements
with algorithm execution costs.

All three algorithms now use original-source Matched with Owner code-generation
options. The fresh campaign runs Stock/Matched/Owner in every deployment;
see the [full report](../section63/results/report.md).
