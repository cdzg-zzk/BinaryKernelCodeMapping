# Unattended continuation after Clocktime

Installed and enabled on 2026-09-11:
`vkso-evaluation-followup.service`. It is currently inactive; no additional
benchmark is running. The current Clocktime service and its frozen protocol
were not changed.

At boot, the follow-up unit runs only if the Clocktime campaign completion
file exists. Its entry point additionally requires the Clocktime service to
be inactive, no campaign failure marker, and kernel `5.15.0-119-generic`.
The Clocktime controller already returns to that kernel after collecting and
summarizing all 20 steps. On entering the follow-up, the service disables
itself so a later reboot cannot silently repeat the work.

The sequential jobs are:

1. Complete normalized Clocktime coverage/identity audit.
2. Raw writer audit of all 15 UPDATE method directories, including counts,
   headers, sample order, CPU distribution, summaries and normalized values.
3. Three complete deployments of each LZ4/BCH/XZ algorithm, with the full LZ4
   CLI workflow enabled in each LZ4 registration session.
4. Static inspection of the eight fixed prospective applicability cases,
   followed by carrier construction for accepted eligible cases.

There are 18 top-level jobs: one coverage audit, 15 writer audits, the complete
algorithm/application campaign, and the applicability batch. These are jobs,
not 18 new reboots. All follow-up work runs sequentially on the returned
ordinary kernel. A failing job preserves its files and stops later jobs.
There is no automatic retry or overwrite.

Results and status:

```text
test/evaluation/results/followup-service.log
test/evaluation/results/post-clocktime-20260911/state.json
test/evaluation/results/post-clocktime-20260911/clocktime-*.log
test/evaluation/results/post-clocktime-20260911/algorithms/
test/evaluation/results/post-clocktime-20260911/applicability/
```

Read the service state with:

```sh
systemctl show vkso-evaluation-followup.service \
  -p ActiveState -p SubState -p MainPID -p ExecMainStatus
```

The individual runner commands in the other READMEs are manual alternatives.
The enabled follow-up is already scheduled to invoke them; use its logs and
state file for this run instead of starting another campaign alongside it.

The queued application build and live-carrier integration have not yet run.
Their first execution may reveal a build/integration issue, in which case the
retained log is the next debugging input. The queue is not a promise of a
successful result, and its completion is not final Evaluation acceptance.
Clocktime reader/window/ABI/PFN interpretation, group B's full resource and
boundary evidence, BCH/owner-kernel diagnostics, applicability runtime and
adaptation accounting, and final manuscript integration remain goal work.

Verification before installation: the 18-job plan matched the fixed Clocktime
plan; premature execution was rejected without creating a campaign directory;
the service unit passed `systemd-analyze verify`; root Python can import the
checker dependencies. Installation reported enabled/inactive with MainPID 0.
These are orchestration checks, not new performance evidence.
