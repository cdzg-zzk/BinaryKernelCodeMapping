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
                            "BLOCK_SIZES": "4096,65536,1048576", "CLI_ROUNDS": "4"}},
    "bch": {"directory": "test_BCH", "rounds": 11,
            "environment": {"SAMPLE_MS": "10", "CORRECTNESS_VECTORS": "128",
                            "BCH_ALIGNED_INPUTS": "1"}},
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
               "test/evaluation", "vkso", "make_dll", "page_cache_replace",
               "kernel_cgd/function_checker")


def capture_source_files(directory):
    """Preserve actual inputs, including ignored owner sources and new tools."""
    destination = directory / 'source-files'
    destination.mkdir()
    roots = ('make_dll', 'page_cache_replace', 'kernel_cgd/function_checker',
             'kernel_cgd/kerne_type', 'test/test_lz4', 'test/test_BCH',
             'test/test_xz', 'test/test_first_call', 'test/evaluation')
    excluded = {'results', 'build', 'work', 'corpus', '__pycache__', '.git'}
    suffixes = {'.c', '.cpp', '.h', '.S', '.sh', '.py', '.txt', '.json', '.map', '.mk', '.md', '.ld'}
    paths = {ROOT / 'vkso', ROOT / 'kernel_cgd/src/krg.cpp', ROOT / 'kernel_cgd/src/krg'}
    for relative in roots:
        for current, directories, files in os.walk(ROOT / relative):
            directories[:] = [d for d in directories if d not in excluded and not d.startswith('.')]
            for name in files:
                path = Path(current) / name
                if (name == 'Makefile' or path.suffix in suffixes) and not name.endswith('.mod.c'):
                    paths.add(path)
    records = []
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)  # Materialize cooperative-owner header symlinks.
        records.append(dict(path=str(relative), bytes=target.stat().st_size,
                            source_was_symlink=path.is_symlink()))
    write_json(directory / 'source-files.json', {'scope': 'actual source/configuration files and executed KRG binary; excludes outputs/corpora',
                                                'files': records})
    return records


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


def read_observations(algorithm, raw, deployment, *, legacy_lz4=False):
    """Validate the full configured raw matrix and retain repetition identities."""
    rounds = CONFIG[algorithm]["rounds"]
    if algorithm == "lz4":
        backends = ("user-default", "user-nosimd", "kernel-userspace-native",
                    "kernel-userspace-nosimd", "kernel-vkso")
        if not legacy_lz4:
            backends += ("kernel-userspace-libc",)
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


def make_plan(algorithms, count, output, cpu, kernel, with_lz4_workflow=False, with_kernel_cost=False, with_lz4_setup=False):
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
            environment["RUN_LZ4_SETUP"] = str(int(with_lz4_setup and algorithm == "lz4"))
            environment["RUN_KERNEL_COST"] = str(int(with_kernel_cost))
            environment["RUN_CLI_WORKFLOW"] = str(int(with_lz4_workflow and algorithm == "lz4"))
            entries.append({"deployment": directory.name, "algorithm": algorithm,
                            "directory": str(directory), "environment": environment,
                            "command": ["bash", str(source / "run.sh")]})
    return {"kernel": kernel, "cpu": cpu, "deployments_per_algorithm": count,
            "with_lz4_workflow": with_lz4_workflow, "with_kernel_cost": with_kernel_cost, "with_lz4_setup": with_lz4_setup,
            "sampling_unit": "complete owner load/export/register/benchmark/restore/unload",
            "boot_scope": "same boot unless recorded boot_id values differ",
            "entries": entries}


def execute(plan, output, resume=False):
    host_ready(plan["kernel"])
    if plan["cpu"] not in os.sched_getaffinity(0):
        raise RuntimeError("requested benchmark CPU is outside current affinity")
    changes = source_snapshot()
    if os.geteuid() != 0:
        subprocess.run(["sudo", "-n", "true"], check=True)
    recovery = None
    if resume:
        if json.loads((output / 'plan.json').read_text()) != plan:
            raise ValueError('resume must retain the complete original plan')
        # Algorithm/build changes require a fresh campaign. Offline reporting
        # and pre-timing evidence checks may be repaired without resampling.
        for algorithm in CONFIG.values():
            source = ROOT / 'test' / algorithm['directory']
            for folder in ('kmod', 'adapted', 'src', 'userspace', 'config'):
                if not (source / folder).exists():
                    continue
                for path in (source / folder).rglob('*'):
                    if path.suffix not in ('.c', '.h', '.json', '.map') or path.name.endswith('.mod.c'):
                        continue
                    saved = output / 'source-files' / path.relative_to(ROOT)
                    if not saved.exists() or saved.read_bytes() != path.read_bytes():
                        raise ValueError(f'measurement source changed: {path}')
            saved = output / 'source-files' / source.relative_to(ROOT) / 'Makefile'
            if saved.read_bytes() != (source / 'Makefile').read_bytes():
                raise ValueError('user compiler configuration changed')
        recovery = output / ('resume-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        recovery.mkdir()
        capture_source_files(recovery)
        (recovery / 'source-changes.patch').write_bytes(changes)
        if (output / 'failed.json').exists():
            (output / 'failed.json').rename(recovery / 'failed.json')
    else:
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / "plan.json", plan)
        (output / "source-changes.patch").write_bytes(changes)
        capture_source_files(output)
    for entry in plan["entries"]:
        host_ready(plan["kernel"])
        directory = Path(entry["directory"])
        if resume and (directory / 'complete.json').exists():
            from formal_kernel_audit import audit
            audit(directory)
            read_observations(entry['algorithm'], directory / 'results/raw.csv', entry['deployment'])
            continue
        if resume and directory.exists():
            directory.rename(recovery / directory.name)
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
            if entry['algorithm'] == 'lz4' and plan['with_lz4_workflow']:
                cli = directory / 'results/cli-workflow'
                complete = json.loads((cli / 'complete.json').read_text())
                cli_metadata = json.loads((cli / 'metadata.json').read_text())
                if (complete['rows'] != 768 or complete['input_files'] != 12 or
                        cli_metadata['rounds'] != 4 or cli_metadata['block_ids'] != [4, 6] or
                        Path(cli_metadata['backends']['same-source'][0]).name != 'libkernel-userspace-libc.so'):
                    raise ValueError('LZ4 application did not complete the configured libc-baseline matrix')
            if entry['algorithm'] == 'lz4' and plan.get('with_lz4_setup'):
                from setup.compare_audit import audit as audit_setup_comparison, audit_export
                for phase in ('active', 'ready'):
                    report = audit_setup_comparison(directory / 'results' / ('setup-comparison-'+phase),
                        manager_log=directory / 'work/vkso/metadata/page_replace.log')
                    write_json(directory / ('setup-'+phase+'-audit.json'), report)
                write_json(directory / 'setup-export-audit.json',
                    audit_export(directory / 'results/setup-export-stages.tsv'))
            if plan.get('with_kernel_cost'):
                kernel = directory / 'results/kernel-cost'
                name = 'status.json' if entry['algorithm'] == 'bch' else 'collection.json'
                collection = json.loads((kernel / name).read_text())
                if collection['status'] != 'pass' or collection['configuration']['cpu'] != plan['cpu']:
                    raise ValueError('same-owner kernel collection did not complete on selected CPU')
                if entry['algorithm'] == 'bch':
                    if collection['coverage']['timing_rows'] != 1056 or not collection['same_registered_owner']:
                        raise ValueError('BCH kernel matrix is incomplete')
                else:
                    expected_trials = 792 if entry['algorithm'] == 'lz4' else 99
                    if len(collection['trials']) != expected_trials or collection['owner_refcnt_after'] != 1:
                        raise ValueError('LZ4/XZ kernel matrix or owner lifetime is incomplete')
            shutil.copy2(entry["environment"]["MODULE"], directory / "owner.ko")
            commands = directory / 'owner-build-commands'
            commands.mkdir()
            for path in Path(entry['environment']['KMOD_DIR']).glob('.*.cmd'):
                shutil.copy2(path, commands / path.name)
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
    parser.add_argument("--resume", action="store_true",
                        help="continue a stopped campaign, preserving completed deployments")
    parser.add_argument("--with-lz4-workflow", action="store_true")
    parser.add_argument("--with-kernel-cost", action="store_true",
                        help="run complete kernel workload in each existing registration after user measurement")
    parser.add_argument("--with-lz4-setup", action="store_true",
                        help="compare full LZ4 tasks with traced/untraced active and ready-carrier commands")
    args = parser.parse_args()
    if args.deployments < 1 or len(set(args.algorithms)) != len(args.algorithms):
        parser.error("use a positive deployment count and distinct algorithms")
    if (args.with_lz4_workflow or args.with_lz4_setup) and "lz4" not in args.algorithms:
        parser.error("the file workflow requires lz4 in --algorithms")
    output = args.output.resolve()
    if args.resume and (not args.execute or not (output / 'plan.json').exists()):
        parser.error('resume requires --execute and an existing plan')
    if output.exists() and not args.resume:
        parser.error("output already exists; use a fresh campaign path")
    plan = make_plan(args.algorithms, args.deployments, output, args.cpu, args.kernel,
                     args.with_lz4_workflow, args.with_kernel_cost, args.with_lz4_setup)
    if args.execute:
        execute(plan, output, resume=args.resume)
    else:
        print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
