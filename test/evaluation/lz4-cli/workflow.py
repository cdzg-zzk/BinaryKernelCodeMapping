#!/usr/bin/env python3
"""Measure complete upstream LZ4 CLI file operations inside an active export."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import subprocess
import time


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(1024 * 1024):
            value.update(data)
    return value.hexdigest()


def warm(path):
    with path.open("rb") as stream:
        while stream.read(1024 * 1024):
            pass


def run_cli(command, environment, log, input_path=None):
    if input_path is not None:
        warm(input_path)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with log.open("w") as stream:
        start = time.perf_counter_ns()
        subprocess.run(command, env=environment, stdout=stream,
                       stderr=subprocess.STDOUT, check=True)
        wall_ns = time.perf_counter_ns() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"wall_ns": wall_ns,
            "child_user_seconds": after.ru_utime - before.ru_utime,
            "child_system_seconds": after.ru_stime - before.ru_stime,
            "child_minor_faults": after.ru_minflt - before.ru_minflt,
            "child_major_faults": after.ru_majflt - before.ru_majflt}


def summarize(rows, output):
    grouped = {}
    for row in rows:
        key = (row["round"], row["block_id"], row["backend"], row["operation"])
        group = grouped.setdefault(key, {"plain_bytes": 0, "wall_ns": 0, "output_bytes": 0})
        for field in group:
            group[field] += row[field]
    aggregates = []
    for key, counters in sorted(grouped.items()):
        r, block_id, backend, operation = key
        aggregates.append({"round": r, "block_id": block_id, "backend": backend,
                           "operation": operation, **counters,
                           "mib_per_second": counters["plain_bytes"] * 1e9 /
                           (1048576 * counters["wall_ns"])})
    with (output / "rounds.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(aggregates[0]))
        writer.writeheader()
        writer.writerows(aggregates)
    paired = {(r["round"], r["block_id"], r["operation"], r["backend"]): r for r in aggregates}
    lines = ["# LZ4 file workflow within one deployment", "",
             "Throughput uses total plain bytes divided by summed full CLI wall time across files.",
             "Each command includes process/loader startup, frame work, allocation and buffered file I/O.",
             "Inputs are pre-read before each command. Output closes without a durability flush.",
             "Compression uses each backend's encoder; decompression uses identical stock-encoded frames.",
             "Ratios below compare matched outer rounds within this deployment; they are not confidence intervals.",
             "", "| Block bytes | Operation | Baseline | Median VKSO/baseline wall-time ratio | Min–max |",
             "| ---: | --- | --- | ---: | ---: |"]
    for block in sorted({r["block_id"] for r in rows}):
        for operation in ("compress", "decompress"):
            for baseline in ("same-source", "upstream-dso", "stock-cli"):
                values = [paired[(r, block, operation, "kernel-vkso")]["wall_ns"] /
                          paired[(r, block, operation, baseline)]["wall_ns"]
                          for r in sorted({row["round"] for row in rows})]
                lines.append(f"| {1 << (8 + 2 * block)} | {operation} | {baseline} | "
                             f"{statistics.median(values):.6f} | {min(values):.6f}–{max(values):.6f} |")
    (output / "summary.md").write_text("\n".join(lines) + "\n")


def collect(args):
    paths = []
    for line in args.manifest.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            p = Path(line)
            paths.append((p if p.is_absolute() else args.manifest.parent / p).resolve())
    if not paths or len(set(paths)) != len(paths) or any(not p.is_file() for p in paths):
        raise ValueError("manifest must contain distinct existing corpus files")
    args.output.mkdir(parents=True, exist_ok=False)
    logs = args.output / "logs"
    scratch = args.output / "files"
    logs.mkdir()
    scratch.mkdir()
    inputs = [{"path": str(p), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]
    base_environment = os.environ.copy()
    for key in ("VKSO_LZ4_LIBRARY", "VKSO_LZ4_API", "VKSO_LZ4_TRACE", "LD_PRELOAD"):
        base_environment.pop(key, None)
    base_environment["LC_ALL"] = "C"
    backends = {"stock-cli": None,
                "upstream-dso": (args.upstream.resolve(), "user"),
                "same-source": (args.same_source.resolve(), "kernel"),
                "kernel-vkso": (args.kernel.resolve(), "kernel")}

    def invocation(name, arguments, trace=None):
        environment = dict(base_environment)
        if backends[name] is None:
            binary = args.stock
        else:
            binary = args.adapted
            library, api = backends[name]
            environment.update(VKSO_LZ4_LIBRARY=str(library), VKSO_LZ4_API=api)
            if trace is not None:
                environment["VKSO_LZ4_TRACE"] = str(trace)
        return ["taskset", "-c", str(args.cpu), str(binary.resolve()), *arguments], environment

    def compression(block, source, target):
        return ["-q", "-f", "-1", f"-B{block}", "-BI", "--content-size", str(source), str(target)]

    def decompression(source, target):
        return ["-q", "-f", "-d", "--no-sparse", str(source), str(target)]

    helper_evidence = json.loads(args.helper_evidence.read_text())
    if (helper_evidence['status'] != 'pass' or Path(helper_evidence['library']).resolve() != args.kernel.resolve()
            or Path(helper_evidence['same_source']).resolve() != args.same_source.resolve()
            or {h['name'] for h in helper_evidence['helpers']} != {'memcpy', 'memmove', 'memset'}):
        raise ValueError('helper audit does not identify these complete backends')
    (args.output / 'helper-targets.json').write_text(json.dumps(helper_evidence, indent=2)+'\n')
    metadata = {"cpu": args.cpu, "uid": os.getuid(), "euid": os.geteuid(),
                "rounds": args.rounds, "block_ids": args.block_ids,
                "inputs": inputs, "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                "kernel": os.uname().release, "source": "upstream LZ4 1.9.3 CLI/frame implementation",
                "backends": {name: None if b is None else [str(b[0]), b[1]] for name, b in backends.items()},
                "cache": "input pre-read; buffered output without fsync",
                "timing": "parent wall time around taskset/CLI process launch and completion",
                "diagnostic": "call counters enabled only in separate untimed invocations",
                "same_source_helper_policy": "resolved libc targets matched to the carrier ABI bridges; scalar algorithm body"}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    common_frames = {}
    for block in args.block_ids:
        for i, source in enumerate(paths):
            target = scratch / f"common-{block}-{i}.lz4"
            command, environment = invocation("stock-cli", compression(block, source, target))
            run_cli(command, environment, logs / f"prepare-{block}-{i}.log")
            common_frames[(block, i)] = target

    # Exercise full frame paths with tracing separately from the timed commands.
    for block in args.block_ids:
        for name in backends:
            if name == "stock-cli":
                continue
            encoded, decoded = scratch / "diagnostic.lz4", scratch / "diagnostic.out"
            for operation, arguments in (
                ("compress", compression(block, paths[0], encoded)),
                ("decompress", decompression(encoded, decoded)),
            ):
                trace = logs / f"trace-{block}-{name}-{operation}.txt"
                command, environment = invocation(name, arguments, trace)
                run_cli(command, environment, logs / f"trace-{block}-{name}-{operation}.log")
                values = dict(line.split("=", 1) for line in trace.read_text().splitlines())
                if int(values[f"{operation}_calls"]) <= 0:
                    raise ValueError(f"{name}/{operation}: selected API was not exercised")
                for field in ("compress_dso", "decompress_dso"):
                    if Path(values[field]).resolve() != backends[name][0]:
                        raise ValueError(f"{name}: resolved API came from another DSO")
            if digest(decoded) != inputs[0]["sha256"]:
                raise ValueError("diagnostic round trip differs from input")
            encoded.unlink()
            decoded.unlink()

    rows = []
    names = list(backends)
    with (args.output / "raw.csv").open("w", newline="") as stream:
        writer = None
        for r in range(args.rounds):
            for block_position in range(len(args.block_ids)):
                block = args.block_ids[(block_position + r) % len(args.block_ids)]
                for i, source in enumerate(paths):
                    offset = (r + i + block) % len(names)
                    for name in names[offset:] + names[:offset]:
                        for operation in ("compress", "decompress"):
                            tag = f"r{r}-b{block}-i{i}-{name}-{operation}"
                            target = scratch / f"{tag}.out"
                            if operation == "compress":
                                timed_input = source
                                arguments = compression(block, source, target)
                            else:
                                timed_input = common_frames[(block, i)]
                                arguments = decompression(timed_input, target)
                            command, environment = invocation(name, arguments)
                            values = run_cli(command, environment, logs / f"{tag}.log", timed_input)
                            row = {"round": r, "block_id": block, "input": source.name,
                                   "backend": name, "operation": operation,
                                   "plain_bytes": inputs[i]["bytes"],
                                   "input_bytes": timed_input.stat().st_size,
                                   "output_bytes": target.stat().st_size, **values}
                            # Stock decoding validates every backend's generated frame.
                            checked = target
                            if operation == "compress":
                                checked = scratch / "verification.out"
                                verify, verify_environment = invocation("stock-cli", decompression(target, checked))
                                run_cli(verify, verify_environment, logs / f"{tag}-verify.log")
                            if digest(checked) != inputs[i]["sha256"]:
                                raise ValueError(f"incorrect complete file output: {tag}")
                            if writer is None:
                                writer = csv.DictWriter(stream, fieldnames=list(row))
                                writer.writeheader()
                            writer.writerow(row)
                            stream.flush()
                            rows.append(row)
                            if checked != target:
                                checked.unlink()
                            target.unlink()
    expected = args.rounds * len(args.block_ids) * len(paths) * len(names) * 2
    if len(rows) != expected:
        raise ValueError("incomplete application matrix")
    summarize(rows, args.output)
    # Common compressed inputs are reproducible and need not occupy each deployment archive.
    for frame in common_frames.values():
        frame.unlink()
    (args.output / "complete.json").write_text(json.dumps({"rows": len(rows),
        "input_files": len(paths), "output_checks": "all complete file outputs matched",
        "scope": "one registration session; selected API call paths verified in separate diagnostics"}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stock", "adapted", "kernel", "same-source", "upstream", "manifest", "output", "helper-evidence"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--cpu", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--block-ids", type=int, choices=(4, 5, 6, 7), nargs="+", default=[4, 6])
    args = parser.parse_args()
    if args.rounds < 1 or len(set(args.block_ids)) != len(args.block_ids):
        parser.error("use positive rounds and distinct block IDs")
    if args.output.exists():
        parser.error("output directory already exists")
    collect(args)


if __name__ == "__main__":
    main()
