#!/usr/bin/env python3
"""Collect one planned boot with isolated carriers and unchanged runtime code."""
import argparse
import contextlib
import csv
import importlib.util
import json
import os
import random
import signal
import shutil
import subprocess
import time
from pathlib import Path

from campaign import digest, manifest, pending, freeze_protocol
from carrier import materialize

HERE = Path(__file__).resolve().parent
WRITER = Path("/sys/kernel/debug/timekeeping_update_bench")
FIELDS = ["variant", "role", "scenario", "metric", "unit", "protocol", "method",
          "boot_id", "image_sha256", "round", "value"]


def run(argv, *, output=None, env=None):
    if output:
        with Path(output).open("w") as stream:
            return subprocess.run([str(a) for a in argv], env=env, stdout=stream, check=True)
    return subprocess.run([str(a) for a in argv], env=env, check=True, capture_output=True, text=True)


def rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


@contextlib.contextmanager
def registered(package):
    manager = package / "manager"
    carrier = package / "libkernel.so"
    page_map = package / "page_mappings.txt"
    # Fresh test copies must reach disk before their cached pages are replaced.
    # The existing registration module expects clean file-backed pages.
    with carrier.open('rb') as stream:
        os.fsync(stream.fileno())
    run([manager, "validate", carrier, page_map])
    try:
        run([manager, "replace", carrier, page_map])
        yield
    finally:
        run([manager, "restore", carrier, page_map])


def clone_package(package, target):
    target.mkdir()
    for name in ("libkernel.so", "page_mappings.txt", "vkso-time-bench", "raw-abi-matrix",
                 "vkso-abi-matrix", "manager", "page_cache_replace.ko", "vkso_m09_clock.ko"):
        shutil.copy2(package / name, target / name)


def append(measurements, identity, scenario, metric, unit, protocol, repeat, value):
    measurements.append({**identity, "scenario": scenario, "metric": metric, "unit": unit,
                         "protocol": protocol, "round": repeat, "value": value})


def writer_summary(path):
    spec = importlib.util.spec_from_file_location("writer_analysis", HERE.parent / "update-bench/compare-update.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_writer(path)


def record_writer(path, seconds):
    try:
        (WRITER / "control").write_text("start\n")
        time.sleep(seconds)
    finally:
        (WRITER / "control").write_text("stop\n")
    shutil.copyfile(WRITER / "samples", path)


def add_writer(measurements, identity, scenario, repeat, path, protocol):
    values = writer_summary(path)
    for name in ("mean_corrected_cycles", "median_corrected_cycles", "p95_corrected_cycles", "p99_corrected_cycles"):
        append(measurements, identity, scenario, name, "TSC cycles/update", protocol, repeat, values[name])
    # Preserve counts and the actual CPUs; do not infer the writer's CPU from affinity.
    (path.with_suffix(".json")).write_text(json.dumps(values, indent=2) + "\n")


def cpu_list(value):
    result = set()
    for part in value.split(","):
        if "-" in part:
            first, last = map(int, part.split("-"))
            result.update(range(first, last + 1))
        elif part.isdigit():
            result.add(int(part))
    return result


def check_environment(cpus):
    if Path("/sys/devices/system/clocksource/clocksource0/current_clocksource").read_text().strip() != "tsc":
        raise ValueError("TSC clocksource required")
    smt = Path("/sys/devices/system/cpu/smt/active")
    if smt.exists() and smt.read_text().strip() != "0":
        raise ValueError("SMT must be disabled")
    cmdline = Path("/proc/cmdline").read_text().split()
    parameters = dict(x.split("=", 1) for x in cmdline if "=" in x)
    if "nokaslr" not in cmdline:
        raise ValueError("packaged carrier addresses require nokaslr")
    for key in ("isolcpus", "nohz_full", "rcu_nocbs"):
        if not set(cpus) <= cpu_list(parameters.get(key, "")):
            raise ValueError(f"{key} does not cover measurement CPUs {cpus}; use the revision boot entry")
    for path, expected in (
        ("intel_pstate/no_turbo", "1"), ("intel_pstate/min_perf_pct", "100"),
        ("intel_pstate/max_perf_pct", "100")):
        file = Path("/sys/devices/system/cpu") / path
        if file.exists() and file.read_text().strip() != expected:
            raise ValueError(f"set {file} to {expected} before formal collection")


def collect_read(package, output, backend, identity, args, measurements):
    env = {**os.environ, "LD_LIBRARY_PATH": str(package)}
    runner = ["setarch", os.uname().machine, "-R", package / "vkso-time-bench"]
    # Preserve the existing binary and 31-round/7-process protocol. PMU is separate.
    global_round = 0
    for process in range(args.processes):
        count = args.rounds // args.processes + (process < args.rounds % args.processes)
        path = output / f"read-process-{process:02d}.csv"
        run([*runner, "--backend", backend, "--mode", "perf", "--cpu", args.cpu,
             "--iterations", args.iterations, "--warmup", args.warmup,
             "--repeats", count, "--pmu", 0], output=path, env=env)
        data = rows(path)
        public = [r for r in data if r['path'] != 'syscall']
        if len(public) != 20 * count or len({(r['api'], r['repeat']) for r in public}) != len(public):
            raise ValueError('incomplete or duplicate public READ measurements')
        for item in data:
            if item["path"] == "syscall":
                continue
            append(measurements, identity, item["api"], "reader_cycles", "TSC cycles/call",
                   "direct-user-api-steady-batch-v3", global_round + int(item["repeat"]),
                   float(item["tsc_cycles_per_call"]))
        global_round += count
    kernel = Path("/sys/kernel/debug/vkso_kernel_reader")
    (kernel / "control").write_text(f"{args.cpu} {args.iterations} {args.rounds} {args.warmup}\n")
    destination = output / "kernel-reader.csv"
    shutil.copyfile(kernel / "samples", destination)
    data = rows(destination)
    if len(data) != 3 * args.rounds or len({(r['api'], r['round']) for r in data}) != len(data):
        raise ValueError('incomplete or duplicate kernel READ measurements')
    for item in data:
        if int(item["cpu"]) != args.cpu:
            raise ValueError("kernel reader ran on a different CPU")
        append(measurements, identity, item["api"], "kernel_reader_cycles", "TSC cycles/call",
               "ordinary-kernel-api-batch-v1", item["round"], int(item["total_tsc_cycles"]) / int(item["iterations"]))


def collect_update(package, output, backend, identity, args, measurements):
    env = {**os.environ, "LD_LIBRARY_PATH": str(package)}
    cpus = args.reader_cpus.split(",")
    scenarios = [(op, count, rate) for op in ("monotonic", "monotonic_raw", "monotonic_coarse")
                 for count in (1, 2, 3) for rate in (0, args.rate)]
    rng = random.Random(args.block)
    for repeat in range(args.update_rounds):
        order = [None, *scenarios]
        rng.shuffle(order)
        for entry in order:
            if entry is None:
                scenario = "idle"
                target = output / scenario
                target.mkdir(exist_ok=True)
                path = target / f"round-{repeat:02d}-writer.csv"
                # Match the multi-reader recorder's interior window duration.
                guard = 1 if args.seconds > 2 else .1
                record_writer(path, args.seconds - 2 * guard)
                add_writer(measurements, identity, scenario, repeat, path, "full-writer-idle-v1")
                continue
            op, count, rate = entry
            scenario = f"{op}/readers-{count}/rate-{rate}"
            target = output / scenario
            target.mkdir(parents=True, exist_ok=True)
            reader = target / f"round-{repeat:02d}-reader.csv"
            writer = target / f"round-{repeat:02d}-writer.csv"
            # A fixed-rate run uses the SAME batches on Raw/VKSO; rate includes warmups.
            iterations = args.iterations if not rate else args.paced_iterations
            warmup = args.warmup if not rate else args.paced_warmup
            try:
                run(["setarch", os.uname().machine, "-R", args.multireader,
                     "--backend", backend, "--cpus", ",".join(cpus[:count]), "--seconds", args.seconds,
                     "--operation", op, "--iterations", iterations, "--warmup", warmup,
                     "--rate", rate, "--writer-control", WRITER / "control"], output=reader, env=env)
            finally:
                (WRITER / "control").write_text("stop\n")
            shutil.copyfile(WRITER / "samples", writer)
            items = rows(reader)
            if len(items) != count:
                raise ValueError("missing multi-reader results")
            writer_start, writer_end = int(items[0]["writer_start_ns"]), int(items[0]["writer_end_ns"])
            if max(int(r["start_ns"]) for r in items) >= writer_start or min(int(r["end_ns"]) for r in items) <= writer_end:
                raise ValueError("writer recording was not inside all readers' load windows")
            span = max(int(r["end_ns"]) for r in items) - min(int(r["start_ns"]) for r in items)
            rates = []
            for item in items:
                reader_id = item["reader"]
                throughput = (int(item["measured_calls"]) + int(item["conditioning_calls"])) * 1e9 / (
                    int(item["end_ns"]) - int(item["start_ns"]))
                rates.append(throughput)
                append(measurements, identity, scenario + "/reader-" + reader_id, "reader_cycles",
                       "TSC cycles/call", item["measurement_window"], repeat, float(item["tsc_cycles_per_call"]))
                append(measurements, identity, scenario + "/reader-" + reader_id, "actual_total_rate",
                       "calls/s", item["measurement_window"], repeat, throughput)
                append(measurements, identity, scenario + "/reader-" + reader_id, 'late_batches',
                       'batches', item['measurement_window'], repeat, int(item['late_batches']))
            total = sum(int(r["measured_calls"]) + int(r["conditioning_calls"]) for r in items) * 1e9 / span
            append(measurements, identity, scenario, "total_rate", "calls/s", items[0]["measurement_window"], repeat, total)
            append(measurements, identity, scenario, "jain_fairness", "fraction", items[0]["measurement_window"],
                   repeat, sum(rates) ** 2 / (count * sum(r * r for r in rates)))
            add_writer(measurements, identity, scenario, repeat, writer, "full-writer-load-interior-v1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--multireader", required=True, type=Path)
    parser.add_argument("--kernel-module", required=True, type=Path)
    parser.add_argument("--cpu", default=2, type=int)
    parser.add_argument("--reader-cpus", default="1,2,3")
    parser.add_argument("--rounds", default=31, type=int)
    parser.add_argument("--processes", default=7, type=int)
    parser.add_argument("--update-rounds", default=15, type=int)
    parser.add_argument("--iterations", default=500000, type=int)
    parser.add_argument("--warmup", default=10000, type=int)
    parser.add_argument("--seconds", default=15, type=int)
    parser.add_argument("--stabilize-seconds", default=120, type=int)
    parser.add_argument("--rate", default=1000000, type=int, help="total calls/s/reader, in batches")
    parser.add_argument("--paced-iterations", default=10000, type=int)
    parser.add_argument("--paced-warmup", default=1000, type=int)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("collection requires root on the research kernel")
    def stop_collection(signum, frame):
        raise KeyboardInterrupt(f"collection interrupted by signal {signum}")
    signal.signal(signal.SIGTERM, stop_collection)
    if not 0 < args.processes <= args.rounds or min(args.update_rounds, args.iterations, args.seconds,
                                                   args.rate, args.paced_iterations) <= 0:
        parser.error("invalid sample counts")
    cpus = [int(c) for c in args.reader_cpus.split(",")]
    if len(cpus) != 3 or len(set(cpus)) != 3 or 0 in cpus:
        parser.error("three distinct reader CPUs required; CPU 0 is reserved for control/writer")
    if (args.cpu not in cpus or args.iterations > 1000000 or args.rounds > 1000
            or not 0 <= args.warmup <= 1000000 or args.stabilize_seconds < 0
            or not 0 <= args.paced_warmup <= 1000000 or args.seconds > 3600):
        parser.error('parameters exceed the reader protocol bounds')
    plan = json.loads((args.campaign / "plan.json").read_text())
    step = pending(args.campaign, plan)
    if step is None:
        raise SystemExit("campaign already complete")
    args.block = step["block"]
    check_environment(cpus if step["role"] == "update" else [args.cpu])
    config = plan["packages"][step["role"]]
    package = Path(config["path"])
    if digest(package / "boot-manifest.txt") != config["manifest_sha256"]:
        raise ValueError("package changed since planning")
    subprocess.run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], cwd=package, check=True)
    if os.uname().release != "5.15.198":
        raise ValueError("formal collection requires the packaged 5.15.198 kernel")
    failure_taints = (1 << 7) | (1 << 9)  # kernel oops and WARN, not out-of-tree modules
    if int(Path('/proc/sys/kernel/tainted').read_text()) & failure_taints:
        raise ValueError('kernel already has an oops/WARN; retain logs and use a clean boot')
    probe = run([package / "vkso-time-bench", "--probe"]).stdout
    if f"backend={step['backend']}\n" not in probe:
        raise ValueError("wrong booted backend")
    cmdline = Path("/proc/cmdline").read_text().strip()
    prefix = "vkso-final" if step["role"] == "read" else "vkso-update"
    expected = f"{prefix}-{step['backend']}-{config['variant']}-5.15.198.bzImage"
    boot_image = next((x.split("=", 1)[1] for x in cmdline.split() if x.startswith("BOOT_IMAGE=")), "")
    if Path(boot_image).name != expected or digest(Path("/boot") / expected) != digest(package / f"{step['backend']}-bzImage"):
        raise ValueError("boot image/package mismatch")
    running_config = subprocess.check_output(["zcat", "/proc/config.gz"])
    if running_config != (package / f"{step['backend']}.config").read_bytes():
        raise ValueError("running configuration mismatch")
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    for file in args.campaign.glob("step-*/complete.json"):
        if json.loads(file.read_text())["boot_id"] == boot_id:
            raise ValueError("new independent step requires a new boot")
    tools = {name: HERE / name for name in
             ('collect.py', 'carrier.py', 'footprint.py', 'campaign.py', 'analyze.py', 'boot.py')}
    tools.update(multireader=args.multireader, kernel_module=args.kernel_module,
                 writer_parser=HERE.parent / 'update-bench/compare-update.py')
    protocol_sha256 = freeze_protocol(args.campaign, args, tools)
    out = args.campaign.resolve() / f"step-{step['index']:03d}"
    out.mkdir()
    os.sched_setaffinity(0, {0})
    metadata = {"step": step, "boot_id": boot_id, "cmdline": cmdline,
                "plan_sha256": digest(args.campaign / "plan.json"), "probe": probe,
                "protocol_sha256": protocol_sha256,
                "parameters": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "multireader_sha256": digest(args.multireader), "kernel_module_sha256": digest(args.kernel_module),
                "legacy_reader_sha256": digest(package / "vkso-time-bench")}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (out / "running.config").write_bytes(running_config)
    run(['lscpu', '-J'], output=out / 'cpu.json')
    environment = {}
    for path in Path('/sys/devices/system/cpu').glob('cpufreq/policy*/scaling_*'):
        if path.is_file():
            environment[str(path)] = path.read_text().strip()
    for path in Path('/sys/devices/system/cpu/intel_pstate').glob('*'):
        if path.is_file():
            environment[str(path)] = path.read_text().strip()
    (out / 'frequency-settings.json').write_text(json.dumps(environment, indent=2) + '\n')
    loaded = []
    measurements = []
    try:
        for file, module in ((package / "vkso_m09_clock.ko", "vkso_m09_clock"),
                             (args.kernel_module, "vkso_kernel_reader")):
            run(["insmod", file]); loaded.append(module)
        if step["backend"] == "vkso":
            run(["insmod", package / "page_cache_replace.ko"]); loaded.append("page_cache_replace")
        for method in step["methods"]:
            target = out / method
            target.mkdir()
            carrier = target / "package"
            clone_package(package, carrier)
            if method == "compact-split":
                with registered(carrier):
                    copied = materialize(carrier / "libkernel.so", carrier / "page_mappings.txt", target / "copied")
                shutil.copyfile(copied / "libkernel.so", carrier / "libkernel.so")
                shutil.copyfile(copied / "page_mappings.txt", carrier / "page_mappings.txt")
            identity = dict(variant=config["variant"], role=step["role"], method=method, boot_id=boot_id,
                            image_sha256=digest(package / f"{step['backend']}-bzImage"))
            context = registered(carrier) if step["backend"] == "vkso" else contextlib.nullcontext()
            with context:
                env = {**os.environ, "LD_LIBRARY_PATH": str(carrier), "VKSO_TEST_DYNAMIC_CLOCK": "/dev/vkso-m09-clock"}
                run([carrier / f"{step['backend']}-abi-matrix"], output=target / "functional.log", env=env)
                if "abi_matrix_status=pass" not in (target / "functional.log").read_text():
                    raise ValueError("ABI matrix did not pass")
                if step["backend"] == "vkso":
                    run(["python3", HERE / "footprint.py", carrier / "libkernel.so",
                         package / "page_mappings.txt", method], output=target / "footprint.json", env=env)
                time.sleep(args.stabilize_seconds)
                if step["role"] == "read":
                    collect_read(carrier, target, step["backend"], identity, args, measurements)
                else:
                    collect_update(carrier, target, step["backend"], identity, args, measurements)
                run(["setarch", os.uname().machine, "-R", carrier / "vkso-time-bench",
                     "--backend", step["backend"], "--mode", "seq", "--cpu", args.cpu,
                     "--seq-iterations", 100000000], output=target / "sequence-diagnostic.csv", env=env)
        with (out / "measurements.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(measurements)
    finally:
        errors = []
        if (WRITER / "control").exists():
            try:
                (WRITER / "control").write_text("stop\n")
            except OSError as error:
                errors.append(str(error))
        for module in reversed(loaded):
            try:
                run(["rmmod", module])
            except subprocess.CalledProcessError as error:
                errors.append(str(error))
        if errors:
            raise RuntimeError('collection cleanup failed: ' + '; '.join(errors))
    run(['dmesg'], output=out / 'kernel.log')
    if int(Path('/proc/sys/kernel/tainted').read_text()) & failure_taints:
        raise ValueError('kernel reported an oops/WARN during collection; see kernel.log')
    metadata['measurements_sha256'] = digest(out / 'measurements.csv')
    (out / "complete.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
