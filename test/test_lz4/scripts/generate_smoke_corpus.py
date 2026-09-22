#!/usr/bin/env python3
import argparse
import random
from pathlib import Path


def repeat_to_size(seed: bytes, size: int) -> bytes:
    return (seed * ((size + len(seed) - 1) // len(seed)))[:size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size-mib", type=int, default=4)
    args = parser.parse_args()

    size = args.size_mib * 1024 * 1024
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "zeros.bin").write_bytes(bytes(size))
    (args.output / "text.bin").write_bytes(
        repeat_to_size(
            b"Binary kernel code mapping: deterministic LZ4 workload.\n", size
        )
    )
    structured = bytearray(size)
    for offset in range(0, size, 64):
        line = f'{{"offset":{offset},"kind":"lz4","value":{offset % 997}}}\n'.encode()
        structured[offset : offset + min(64, size - offset)] = repeat_to_size(
            line, min(64, size - offset)
        )
    (args.output / "structured.bin").write_bytes(structured)
    rng = random.Random(0x4C5A34)
    (args.output / "random.bin").write_bytes(rng.randbytes(size))
    (args.output / "manifest.txt").write_text(
        "zeros.bin\ntext.bin\nstructured.bin\nrandom.bin\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

