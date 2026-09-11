#!/usr/bin/env python3
"""Plan and advance balanced Clocktime boot collections; never reboot implicitly."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PARAMETERS = ('cpu', 'reader_cpus', 'rounds', 'processes', 'update_rounds', 'iterations',
              'warmup', 'seconds', 'stabilize_seconds', 'rate', 'paced_iterations', 'paced_warmup')


def freeze_protocol(root, args, files):
    """Freeze sample allocation and executable identities at the first collection."""
    protocol = {'parameters': {key: getattr(args, key) for key in PARAMETERS},
                'tools': {name: digest(path) for name, path in files.items()}}
    path = root / 'protocol.json'
    if path.exists():
        if json.loads(path.read_text()) != protocol:
            raise ValueError('parameters or tools changed within one campaign; create a new campaign')
    else:
        with path.open('x') as stream:
            stream.write(json.dumps(protocol, indent=2) + '\n')
    return digest(path)


def manifest(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(root, read_package, update_package, boots, include_copy):
    if boots < 3:
        raise ValueError("formal campaign needs at least three boots per image; five is the default")
    packages = {"read": read_package.resolve(), "update": update_package.resolve()}
    identities = {}
    for role, package in packages.items():
        subprocess.run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], cwd=package, check=True)
        info = manifest(package / "boot-manifest.txt")
        if info["update_bench"] != str(int(role == "update")):
            raise ValueError("recorder configuration does not match collection role")
        identities[role] = {"path": str(package), "manifest_sha256": digest(package / "boot-manifest.txt"),
                            "variant": info["build_variant"], "source": info["vkso_source_tree_sha256"]}
    if len({r["variant"] for r in identities.values()}) != 1 or len({r["source"] for r in identities.values()}) != 1:
        raise ValueError("read/update packages use different methods or build regimes")
    steps = []
    for block in range(boots):
        for role in ("read", "update"):
            backends = ("raw", "vkso") if block % 2 == 0 else ("vkso", "raw")
            for backend in backends:
                methods = ["raw"] if backend == "raw" else ["vkso"]
                if backend == "vkso" and include_copy:
                    methods = ["vkso", "compact-split"] if block % 2 == 0 else ["compact-split", "vkso"]
                steps.append(dict(index=len(steps), block=block, role=role, backend=backend, methods=methods))
    root.mkdir(parents=True, exist_ok=False)
    plan = {"schema": 1, "packages": identities, "boots_per_image": boots,
            "statistics": "boots; compact-split/VKSO paired within a boot", "steps": steps}
    (root / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def pending(root, plan):
    boot_ids = set()
    for step in plan["steps"]:
        record = root / f"step-{step['index']:03d}" / "complete.json"
        if not record.exists():
            return step
        data = json.loads(record.read_text())
        if data["boot_id"] in boot_ids:
            raise ValueError("independent steps reused one boot_id")
        if data["step"] != step or data["plan_sha256"] != digest(root / "plan.json"):
            raise ValueError("completed step does not match the campaign")
        if data['protocol_sha256'] != digest(root / 'protocol.json'):
            raise ValueError('completed step uses a different measurement protocol')
        if data['measurements_sha256'] != digest(record.parent / 'measurements.csv'):
            raise ValueError('completed measurements changed or are missing')
        boot_ids.add(data["boot_id"])
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("root", type=Path)
    prepare.add_argument("--read-package", required=True, type=Path)
    prepare.add_argument("--update-package", required=True, type=Path)
    prepare.add_argument("--boots", default=5, type=int)
    prepare.add_argument("--without-copy", action="store_true")
    status = commands.add_parser("status")
    status.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        plan = create(args.root, args.read_package, args.update_package, args.boots, not args.without_copy)
    else:
        plan = json.loads((args.root / "plan.json").read_text())
    step = pending(args.root, plan)
    if step is None:
        print("all planned boot collections complete")
    else:
        print(json.dumps({"next": step, "package": plan["packages"][step["role"]],
                          "remaining_steps": len(plan["steps"]) - step["index"]}, indent=2))


if __name__ == "__main__":
    main()
