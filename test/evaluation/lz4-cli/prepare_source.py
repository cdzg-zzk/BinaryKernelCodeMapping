#!/usr/bin/env python3
"""Prepare the unmodified 1.9.3 CLI from the existing algorithm source archive."""
from pathlib import Path
import hashlib
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / "test/test_lz4/.cache/lz4-1.9.3.tar.gz"
SHA256 = "030644df4611007ff7dc962d981f390361e6c97a34e5cbc393ddfbe019ffe2c1"
URL = "https://github.com/lz4/lz4/archive/refs/tags/v1.9.3.tar.gz"


def main():
    if not ARCHIVE.exists():
        ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != SHA256:
            raise SystemExit("unexpected LZ4 release archive")
        ARCHIVE.write_bytes(content)
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != SHA256:
        raise SystemExit("unexpected LZ4 release archive")
    with tarfile.open(ARCHIVE) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            path = Path(member.name)
            if path.parts[0] != "lz4-1.9.3" or ".." in path.parts:
                raise ValueError("unexpected release member path")
            if len(path.parts) > 1 and (path.parts[1] in ("lib", "programs")
                                       or path.name == "LICENSE"):
                target = HERE / "vendor" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
    print("Prepared original LZ4 1.9.3 CLI and library sources")


if __name__ == "__main__":
    main()
