#!/usr/bin/env python3
"""Repeat complete algorithm deployments, preserving every registration session.

Default invocation only prints the plan. --execute runs the existing full
algorithm runners after checking that the Clocktime service is inactive and
the requested kernel is running. No kernel or VKSO implementation is changed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {
    "lz4": {"directory": "test_lz4", "rounds": 7,
            "environment": {"CORPUS": "silesia", "BENCH_SECONDS": "2",
                            "BLOCK_SIZES": "4096,65536,1048576"}},
    "bch": {"directory": "test_BCH", "rounds": 11,
            "environment": {"SAMPLE_MS": "10", "CORRECTNESS_VECTORS": "128"}},
    "xz": {"directory": "test_xz", "rounds": 7,
           "environment": {"REPEATS": "20",
                           "INPUTS": "/bin/bash /usr/bin/python3 /usr/lib/x86_64-linux-gnu/libc.so.6"}},
}
OWNER_MODULES = {"vkso_lz4", "vkso_bch", "vkso_xz"}


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def source_snapshot():
    """Check Git access before creating a campaign or starting a deployment."""
    def git(*arguments):
        try:
            return subprocess.check_output(["git", *arguments], cwd=ROOT,
                                           stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            detail = error.stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"Git source capture failed before deployment (euid={os.geteuid()}, "
                f"repository owner uid={ROOT.stat().st_uid}): {detail}. "
                "Use the repository owner's normal terminal/sudo session; "
                "repository trust settings are not changed by this runner.") from error

    top = Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != ROOT:
        raise RuntimeError(f"expected repository {ROOT}, Git selected {top}")
    return git("diff", "HEAD", "--", "test/test_lz4", "test/test_BCH", "test/test_xz",
               "test/evaluation", "vkso", "make_dll", "page_cache_replace")


def host_ready(kernel):
    state = subprocess.run(
        ["systemctl", "show", "vkso-clocktime-revision.service",
         "--property=ActiveState", "--value"], capture_output=True, text=True,
        check=True).stdout.strip()
    if state != "inactive":
        raise RuntimeError(f"Clocktime service state is {state!r}; no algorithm run started")
    followup = subprocess.run(
        ["systemctl", "show", "vkso-evaluation-followup.service",
         "--property=ActiveState", "--value"], capture_output=True, text=True)
    if followup.stdout.strip() in {"active", "activating", "reloading", "deactivating"}:
        if "/vkso-evaluation-followup.service" not in Path('/proc/self/cgroup').read_text():
            raise RuntimeError("the unattended follow-up owns the measurement machine; inspect its state")
    if os.uname().release != kernel:
        raise RuntimeError(f"requires kernel {kernel}, found {os.uname().release}")
    loaded = {line.split()[0] for line in Path('/proc/modules').read_text().splitlines()}
    if loaded & OWNER_MODULES:
        raise RuntimeError(f"owner modules still loaded: {sorted(loaded & OWNER_MODULES)}")


def read_observations(algorithm, raw, deployment):
    """Validate the full configured raw matrix and retain repetition identities."""
    rounds = CONFIG[algorithm]["rounds"]
    if algorithm == "lz4":
        backends = ("user-default", "user-nosimd", "kernel-userspace-native",
                    "kernel-userspace-nosimd", "kernel-vkso")
        expected = set(itertools.product(range(rounds), backends,
                                         (4096, 65536, 1048576), ("compress", "decompress")))
    elif algorithm == "bch":
        cases = [(13, t, 512, -1, "init") for t in (4, 8)]
        cases += [(13, t, 512, 0, "encode") for t in (4, 8)]
        cases += [(13, t, 512, e, op) for t in (4, 8) for e in range(t + 1)
                  for op in ("decode-precomputed", "decode-full")]
        expected = {(r, b, *c) for r, b, c in itertools.product(
            range(rounds), ("kernel-vkso", "kernel-native", "author-standalone"), cases)}
    else:
        expected = set(itertools.product(range(rounds), ("native", "kernel-vkso"),
                                         ("bash", "python3", "libc.so.6")))
    seen = set()
    observations = []
    with raw.open(newline="") as stream:
        for row in csv.DictReader(stream):
            backend = row["backend"]
            if algorithm == "lz4":
                r, block = int(row["run"]), int(row["block_size"])
                key = (r, backend, block, row["operation"])
                workload = f"{row['operation']}/block={block}"
                value, unit = float(row["official_mb_per_second"]), "MB/s"
                process = f"round-{r}/block-{block}/{backend}"
                if float(row["harness_seconds"]) != 2 or int(row["input_bytes"]) <= 0:
                    raise ValueError("LZ4 input/window does not match the formal configuration")
            elif algorithm == "bch":
                r = int(row["outer"])
                m, t, size, errors = (int(row[k]) for k in ("m", "t", "len", "errors"))
                key = (r, backend, m, t, size, errors, row["operation"])
                workload = f"m={m}/t={t}/bytes={size}/errors={errors}/{row['operation']}"
                if int(row["iterations"]) <= 0 or int(row["total_ns"]) <= 0:
                    raise ValueError("BCH requires positive timing counters")
                value, unit = int(row["total_ns"]) / int(row["iterations"]), "ns/op"
                process = "benchmark"
            else:
                r = int(row["outer_run"])
                key = (r, backend, row["case"])
                workload = row["case"]
                if (int(row["repeats"]) != 20 or int(row["bytes"]) <= 0
                        or int(row["elapsed_ns"]) <= 0):
                    raise ValueError("XZ input/repeats/timing counters are invalid")
                value = int(row["bytes"]) * 20 * 1e9 / (1048576 * int(row["elapsed_ns"]))
                unit, process = "MiB/s", "benchmark"
            if key not in expected or key in seen:
                raise ValueError(f"unexpected or duplicate {algorithm} observation: {key}")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"invalid measurement: {key}: {value}")
            seen.add(key)
            observations.append({"deployment": deployment, "algorithm": algorithm,
                                 "process_scope": process, "round": r, "backend": backend,
                                 "workload": workload, "value": value, "unit": unit})
    if seen != expected:
        raise ValueError(f"{algorithm}: missing {len(expected - seen)} configured observations")
    return observations


def make_plan(algorithms, count, output, cpu, kernel, with_lz4_workflow=False):
    entries = []
    for block in range(count):
        order = algorithms[block % len(algorithms):] + algorithms[:block % len(algorithms)]
        for algorithm in order:
            config = CONFIG[algorithm]
            source = ROOT / "test" / config["directory"]
            directory = output / f"deployment-{block:02d}-{algorithm}"
            environment = {
                "CPU": str(cpu), "OUTER_RUNS": str(config["rounds"]),
                "RUNTIME_DIR": str(directory), "RESULT_DIR": str(directory / "results"),
                "BUILD_DIR": str(directory / "build"), "WORK_DIR": str(directory / "work"),
                "KMOD_DIR": str(source / "kmod"),
                "MODULE": str(source / "kmod" / f"vkso_{algorithm}.ko"),
                "KERNEL_BUILD": f"/lib/modules/{kernel}/build",
                "SHIM_LIST": str(ROOT / "make_dll/shim.txt"), "VKSO_SKIP_CHECK": "0",
                **config["environment"],
            }
            environment["RUN_CLI_WORKFLOW"] = str(int(with_lz4_workflow and algorithm == "lz4"))
            entries.append({"deployment": directory.name, "algorithm": algorithm,
                            "directory": str(directory), "environment": environment,
                            "command": ["bash", str(source / "run.sh")]})
    return {"kernel": kernel, "cpu": cpu, "deployments_per_algorithm": count,
            "with_lz4_workflow": with_lz4_workflow,
            "sampling_unit": "complete owner load/export/register/benchmark/restore/unload",
            "boot_scope": "same boot unless recorded boot_id values differ",
            "entries": entries}


def execute(plan, output):
    host_ready(plan["kernel"])
    if plan["cpu"] not in os.sched_getaffinity(0):
        raise RuntimeError("requested benchmark CPU is outside current affinity")
    changes = source_snapshot()
    if os.geteuid() != 0:
        subprocess.run(["sudo", "-n", "true"], check=True)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "plan.json", plan)
    (output / "source-changes.patch").write_bytes(changes)
    for entry in plan["entries"]:
        host_ready(plan["kernel"])
        directory = Path(entry["directory"])
        directory.mkdir()
        identity = {"deployment": entry["deployment"], "started_utc": timestamp(),
                    "uid": os.getuid(), "euid": os.geteuid(),
                    "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                    "kernel": os.uname().release,
                    "repo_commit": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
        write_json(directory / "identity.json", identity)
        start = time.monotonic()
        try:
            environment = {**os.environ, **entry["environment"]}
            # Exclude optional diagnostic modes and inherited build parallelism.
            for key in ("GDB_CORRECTNESS", "LD_PRELOAD", "MAKEFLAGS", "MFLAGS"):
                environment.pop(key, None)
            environment["LC_ALL"] = "C"
            with (directory / "runner.log").open("w") as log:
                subprocess.run(entry["command"], cwd=ROOT, env=environment,
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            runner_seconds = time.monotonic() - start
            host_ready(plan["kernel"])
            metadata = (directory / "results/metadata.txt").read_text()
            if "completed_at_utc=" not in metadata:
                raise RuntimeError("runner did not record successful completion")
            observations = read_observations(entry["algorithm"],
                directory / "results/raw.csv", entry["deployment"])
            with (directory / "observations.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(observations[0]))
                writer.writeheader()
                writer.writerows(observations)
            shutil.copy2(entry["environment"]["MODULE"], directory / "owner.ko")
            write_json(directory / "complete.json", {
                **identity, "completed_utc": timestamp(), "observations": len(observations),
                "runner_wall_seconds": runner_seconds,
                "wall_scope": "full runner including build, correctness, measurements, and cleanup",
                "owner_unloaded": True})
        except Exception as error:
            write_json(output / "failed.json", {
                "deployment": entry["deployment"], "time": timestamp(), "error": str(error)})
            raise
    write_json(output / "collection-complete.json", {
        "time": timestamp(), "deployments": len(plan["entries"]),
        "scope": "runner completion and raw matrix validation; scientific analysis is separate"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deployments", type=int, default=3)
    parser.add_argument("--algorithms", nargs="+", choices=CONFIG, default=["bch", "xz", "lz4"])
    parser.add_argument("--cpu", type=int, default=2)
    parser.add_argument("--kernel", default="5.15.0-119-generic")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--with-lz4-workflow", action="store_true")
    args = parser.parse_args()
    if args.deployments < 1 or len(set(args.algorithms)) != len(args.algorithms):
        parser.error("use a positive deployment count and distinct algorithms")
    if args.with_lz4_workflow and "lz4" not in args.algorithms:
        parser.error("the file workflow requires lz4 in --algorithms")
    output = args.output.resolve()
    if output.exists():
        parser.error("output already exists; use a fresh campaign path")
    plan = make_plan(args.algorithms, args.deployments, output, args.cpu, args.kernel,
                     args.with_lz4_workflow)
    if args.execute:
        execute(plan, output)
    else:
        print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
