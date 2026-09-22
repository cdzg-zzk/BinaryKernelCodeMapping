#!/usr/bin/env python3
import argparse
import csv
import re
from pathlib import Path


HEADER = re.compile(r"input\s+(\d+)\s+bytes")
RESULT = re.compile(
    r"^-1\s+(\d+)\s+\(([0-9.]+)\)\s+"
    r"([0-9.]+) MB/s\s+([0-9.]+) MB/s"
)


def parse_log(path: Path) -> list[dict[str, object]]:
    metadata: dict[str, str] = {}
    input_bytes: int | None = None
    result: re.Match[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("-1"):
            key, value = line.split("=", 1)
            if key in {"run", "backend", "block_size", "harness_seconds"}:
                metadata[key] = value
        if match := HEADER.search(line):
            input_bytes = int(match.group(1))
        if match := RESULT.match(line):
            result = match

    required = {"run", "backend", "block_size", "harness_seconds"}
    if required - metadata.keys() or input_bytes is None or result is None:
        raise ValueError(f"incomplete official benchmark log: {path}")

    compressed_bytes = int(result.group(1))
    reported_ratio = float(result.group(2))
    compression_mb_s = float(result.group(3))
    decompression_mb_s = float(result.group(4))
    calculated_ratio = input_bytes / compressed_bytes
    if abs(calculated_ratio - reported_ratio) > 0.001:
        raise ValueError(f"ratio mismatch in {path}")

    common: dict[str, object] = {
        "run": int(metadata["run"]),
        "backend": metadata["backend"],
        "block_size": int(metadata["block_size"]),
        "input_bytes": input_bytes,
        "compressed_bytes": compressed_bytes,
        "compression_ratio": calculated_ratio,
        "harness_seconds": int(metadata["harness_seconds"]),
        "source_log": path.name,
    }
    rows = []
    for operation, speed in (
        ("compress", compression_mb_s),
        ("decompress", decompression_mb_s),
    ):
        rows.append(
            {
                **common,
                "operation": operation,
                "official_mb_per_second": speed,
                "mib_per_second": speed * 1_000_000.0 / (1024.0 * 1024.0),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-libc", action="store_true", help="require the additional same-source libc backend")
    args = parser.parse_args()

    expected_backends = {
        "user-default",
        "user-nosimd",
        "kernel-userspace-native",
        "kernel-userspace-nosimd",
        "kernel-vkso",
    }
    if args.with_libc:
        expected_backends.add("kernel-userspace-libc")
    rows: list[dict[str, object]] = []
    logs = sorted(args.logs.glob("*.log"))
    for path in logs:
        rows.extend(parse_log(path))
    if not rows:
        raise SystemExit("no official benchmark logs found")

    combinations = {
        (int(row["run"]), int(row["block_size"]), str(row["backend"]))
        for row in rows
    }
    runs = sorted({item[0] for item in combinations})
    blocks = sorted({item[1] for item in combinations})
    if runs != list(range(runs[-1] + 1)):
        raise ValueError(f"outer run IDs are not contiguous: {runs}")
    expected = {
        (run, block, backend)
        for run in runs
        for block in blocks
        for backend in expected_backends
    }
    if combinations != expected or len(logs) != len(expected):
        missing = sorted(expected - combinations)
        extra = sorted(combinations - expected)
        raise ValueError(
            f"incomplete benchmark matrix: missing={missing}, extra={extra}, "
            f"logs={len(logs)}, expected_logs={len(expected)}"
        )

    fieldnames = list(rows[0])
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
