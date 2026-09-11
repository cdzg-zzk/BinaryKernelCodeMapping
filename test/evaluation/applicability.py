#!/usr/bin/env python3
"""Inspect the frozen prospective API set and optionally construct carriers.

This tool never registers pages or invokes an exported function. Static
checker exit status, diagnostics, carrier construction, and runtime evidence
are deliberately recorded as separate fields.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from algorithm_deployments import ROOT, host_ready

COUNTS = {
    "visited_functions": "已访问函数",
    "shim_hits": "Shim 命中数",
    "static_references": "静态数据/地址引用数",
    "indirect_control_flow_sites": "间接控制流命中数",
    "instrumentation_sites": "编译器插桩命中数",
    "hard_failures": "致命失败数",
    "missing_symbols": "丢失符号数",
    "unanalyzable_functions": "不可分析函数数",
}


def parse_check(text, returncode):
    clean = re.sub(r"\x1b\[[0-9;]*m", "", text)
    counts = {}
    for key, label in COUNTS.items():
        matches = re.findall(re.escape(label) + r":\s*(\d+)", clean)
        counts[key] = int(matches[-1]) if matches else None
    complete_report = all(value is not None for value in counts.values())
    return {"exit_code": returncode,
            "status": ({0: "checker_pass", 1: "checker_fail", 2: "checker_incomplete"}.get(
                returncode, "tool_execution_error") if complete_report else "tool_execution_error"),
            **counts,
            "scope": "checker result; PASS can retain instrumentation and indirect control-flow sites"}


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def execute(manifest, output, build_carriers):
    host_ready(manifest["prospective_kernel"])
    vmlinux = Path(manifest["prospective_vmlinux"])
    if not vmlinux.is_file():
        raise ValueError(f"missing configured vmlinux: {vmlinux}")
    output.mkdir(parents=True, exist_ok=False)
    save(output / "candidate-manifest.json", manifest)
    identity = {"started_utc": timestamp(), "kernel": os.uname().release,
                "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                "repo_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "vmlinux": str(vmlinux), "vmlinux_bytes": vmlinux.stat().st_size,
                "vmlinux_mtime_ns": vmlinux.stat().st_mtime_ns,
                "build_carriers": build_carriers}
    save(output / "identity.json", identity)
    (output / "vmlinux-notes.txt").write_bytes(subprocess.check_output(["readelf", "-n", str(vmlinux)]))
    shim = ROOT / "make_dll/shim.txt"
    results = []
    shared_krg = None
    for case in manifest["cases"]:
        if case["cohort"] != "prospective":
            results.append({"id": case["id"], "cohort": case["cohort"],
                            "status": "existing_evidence_import_separate"})
            continue
        host_ready(manifest["prospective_kernel"])
        directory = output / case["id"]
        directory.mkdir()
        symbols = directory / "symbols.txt"
        symbols.write_text("\n".join(case["entrypoints"]) + "\n")
        effective_shim = directory / "effective-shim.txt"
        effective_shim.write_text("\n".join(
            line for line in shim.read_text().splitlines()
            if not line.split("#", 1)[0].split()
            or line.split("#", 1)[0].split()[0] not in case["entrypoints"]) + "\n")
        row = {"id": case["id"], "cohort": "prospective", "checks": [],
               "carrier": "not_attempted", "runtime": "not_attempted",
               "semantic_classification": case["semantic_classification"]}
        for api in case["entrypoints"]:
            command = [sys.executable, str(ROOT / "kernel_cgd/function_checker/functions_checker.py"),
                       "-t", api, "-v", str(vmlinux), "-s", str(effective_shim)]
            log = directory / f"checker-{api}.log"
            with log.open("w") as stream:
                process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            row["checks"].append({"api": api, "command": command,
                                  **parse_check(log.read_text(), process.returncode)})
        all_pass = all(check["status"] == "checker_pass" for check in row["checks"])
        if not case["allow_carrier_attempt"]:
            row["carrier"] = "withheld_pending_environment_semantics"
        elif not all_pass:
            row["carrier"] = "not_attempted_after_static_result"
        elif build_carriers:
            workspace = directory / "work"
            subprocess.run(["bash", str(ROOT / "vkso"), "init", str(workspace),
                            "--symbols", str(symbols)], stdout=subprocess.DEVNULL, check=True)
            command = ["bash", str(ROOT / "vkso"), "build", str(workspace),
                       "--symbols", str(symbols), "--vmlinux", str(vmlinux)]
            if shared_krg is not None:
                command += ["--krg", str(shared_krg)]
            with (directory / "carrier-build.log").open("w") as stream:
                built = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            # A core-image KRG may be reused only inside this same boot/build batch.
            local_krg = workspace / "vkso/metadata/out.krg"
            if local_krg.exists():
                shared_krg = local_krg
            row["carrier_command"] = command
            row["carrier_exit_code"] = built.returncode
            row["carrier"] = "constructed_semantics_unverified" if built.returncode == 0 else "construction_failed"
            page_map = workspace / "vkso/metadata/page_mappings.txt"
            if built.returncode == 0:
                if not page_map.is_file():
                    raise RuntimeError("carrier builder returned success without a page map")
                row["page_map"] = str(page_map)
                row["declared_page_rows"] = sum(bool(line.strip()) and not line.lstrip().startswith("#")
                                                for line in page_map.read_text().splitlines())
        results.append(row)
        save(directory / "result.json", row)
        save(output / "results.json", results)
        if any(check["status"] == "tool_execution_error" for check in row["checks"]):
            save(output / "failed.json", {"case": case["id"], "reason": "checker execution failed before a complete result"})
            raise RuntimeError(f"checker execution error for {case['id']}; evidence retained")
    save(output / "results.json", results)
    save(output / "inspection-complete.json", {
        "completed_utc": timestamp(), "prospective_cases": sum(c["cohort"] == "prospective" for c in manifest["cases"]),
        "scope": "static inspection and requested carrier construction; runtime and semantic evaluation remain separate"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=Path(__file__).with_name("applicability-candidates.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-carriers", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.candidates.read_text())
    if args.output.exists():
        parser.error("output already exists; preserve the previous attempt and use a fresh path")
    if args.execute:
        execute(manifest, args.output.resolve(), args.build_carriers)
    else:
        print(json.dumps({"candidates": str(args.candidates), "output": str(args.output),
                          "prospective": [r["id"] for r in manifest["cases"] if r["cohort"] == "prospective"],
                          "build_carriers": args.build_carriers, "register_or_run": False}, indent=2))


if __name__ == "__main__":
    main()
