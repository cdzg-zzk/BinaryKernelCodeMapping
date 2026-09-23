#!/usr/bin/env python3
"""Version collection tooling independently of immutable measured artifacts."""
import hashlib
import json
from pathlib import Path
import shutil
from bundle import PROTOCOL, sha256, write_json, kv_file


def inputs(here):
    bare = here.parent / 'baremetal'
    files = list(here.glob('*.py'))
    files += [bare / n for n in ('collect-case.sh', 'experiment.sh', 'boot-once.sh',
                                'verify-packages.sh', 'experiment.conf')]
    return {str(p.relative_to(here.parent)): p for p in files}


def compatible(here, package):
    """Shell/Python may change; compiled workload/ABI must match packaged sources."""
    build = json.loads((package / 'direct/build.json').read_text())
    if build['protocol'] != PROTOCOL:
        raise ValueError('protocol changed; start a new protocol campaign')
    for name, digest in build['source_hashes'].items():
        if Path(name).suffix in ('.c', '.h') or Path(name).name == 'Makefile':
            p = here.parent / name
            if not p.is_file() or sha256(p) != digest:
                raise ValueError('compiled input changed; rebuild benchmark/package: ' + name)


def snapshot(root, here, packages, config):
    for package in packages:
        compatible(here, package)
    if kv_file(here.parent / 'baremetal/experiment.conf') != config:
        raise ValueError('measurement config changed; start a new campaign')
    paths = inputs(here)
    hashes = {name: sha256(p) for name, p in paths.items()}
    revision = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    dest = root / 'tool-revisions' / revision
    if not dest.exists():
        dest.mkdir(parents=True)
        for name, source in paths.items():
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        write_json(dest / 'revision.json', {'revision': revision, 'files': hashes,
                   'protocol': PROTOCOL, 'scope': 'collection tooling; measured binaries unchanged'})
    validate(dest)
    return revision


def validate(dest):
    data = json.loads((dest / 'revision.json').read_text())
    expected = hashlib.sha256(json.dumps(data['files'], sort_keys=True).encode()).hexdigest()
    if expected != data['revision'] or dest.name != expected:
        raise ValueError('tool revision identity mismatch')
    for name, digest in data['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha256(dest / name) != digest:
            raise ValueError('tool snapshot modified: ' + name)
    return data


def current_matches(dest, here):
    data = validate(dest)
    if data['files'] != {name: sha256(p) for name, p in inputs(here).items()}:
        raise ValueError('collection scripts changed; run ./experiment.sh refresh-tools (no kernel rebuild)')
