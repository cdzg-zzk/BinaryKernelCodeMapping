#!/usr/bin/env python3
"""Run the authorized evaluation follow-up after the final Clocktime reboot."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys

from algorithm_deployments import ROOT, host_ready

HERE = Path(__file__).resolve().parent
CLOCK = ROOT / "test/test_gettime/vkso-tests/revision"
CAMPAIGN = CLOCK / "results/normal-campaign"
OUTPUT = HERE / "results/post-clocktime-20260911"


def stages(output):
    plan = json.loads((CAMPAIGN / "plan.json").read_text())
    jobs = [("clocktime-coverage", [sys.executable, str(CLOCK / "audit_coverage.py"), str(CAMPAIGN)])]
    for step in plan["steps"]:
        if step["role"] == "update":
            for method in step["methods"]:
                name = f"clocktime-writer-{step['index']:03d}-{method}"
                directory = CAMPAIGN / f"step-{step['index']:03d}" / method
                jobs.append((name, [sys.executable, str(CLOCK / "audit_writer_records.py"), str(directory)]))
    jobs += [
        ("algorithm-and-cli-deployments", [sys.executable, str(HERE / "algorithm_deployments.py"),
         "--output", str(output / "algorithms"), "--with-lz4-workflow", "--execute"]),
        ("applicability-inspection", [sys.executable, str(HERE / "applicability.py"),
         "--output", str(output / "applicability"), "--build-carriers", "--execute"]),
    ]
    return jobs


def execute(output, managed_service):
    if not (CAMPAIGN / "campaign-complete.json").is_file() or (CAMPAIGN / "failed.json").exists():
        raise RuntimeError("Clocktime has not completed successfully")
    host_ready("5.15.0-119-generic")
    if output.exists():
        raise RuntimeError("follow-up output already exists; preserve it and inspect instead of rerunning")
    output.mkdir(parents=True)
    if managed_service:
        # A reboot or failure must not silently repeat deployments.
        subprocess.run(["systemctl", "disable", "vkso-evaluation-followup.service"], check=True)
    jobs = stages(output)
    state = {"pid": os.getpid(), "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
             "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "completed_stages": [],
             "jobs": [{"name": name, "command": command} for name, command in jobs]}

    def save_state():
        (output / "state.json").write_text(json.dumps(state, indent=2) + "\n")

    save_state()
    for name, command in jobs:
        state["current_stage"] = name
        save_state()
        print(f"Starting {name}", flush=True)
        # Only audits are pinned to CPU 0. Benchmark runners bind their measured
        # processes to CPU 2 and require that CPU in the inherited allowed mask.
        if name.startswith("clocktime-"):
            command = ["taskset", "-c", "0", *command]
        with (output / f"{name}.log").open("w") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            state["failed_stage"] = name
            state["exit_code"] = result.returncode
            save_state()
            raise RuntimeError(f"{name} exited {result.returncode}; later stages were not started")
        state["completed_stages"].append(name)
        save_state()
        print(f"Completed {name}", flush=True)
    state["current_stage"] = None
    state["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    state["scope"] = "automated checks/collection; scientific analysis and remaining B/C/D/F evidence are separate"
    save_state()
    (output / "collection-complete.json").write_text(json.dumps(state, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--managed-service", action="store_true")
    args = parser.parse_args()
    if args.execute:
        execute(args.output.resolve(), args.managed_service)
    else:
        print(json.dumps({"output": str(args.output), "stages": stages(args.output),
                          "requires": "Clocktime completion, inactive Clocktime service, original algorithm kernel"}, indent=2))
