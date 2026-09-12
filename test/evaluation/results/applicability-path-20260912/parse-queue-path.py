#!/usr/bin/env python3
"""Recover first-enqueue ancestry from a saved log or numbered raw excerpt.

This parses text only. It neither imports nor executes functions_checker.
Counts apply to the supplied input, which may be a selected excerpt rather
than the complete local snapshot.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--numbered', action='store_true')
    parser.add_argument('--start', default='hex_dump_to_buffer')
    parser.add_argument('--target', default='blkg_create')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    pattern = re.compile(r'加入待分析队列: (\S+) <- (\S+) -> (.*)')
    edges = {}
    for number, raw in enumerate(args.input.read_text().splitlines(), 1):
        if args.numbered:
            prefix, raw = raw.split(': ', 1)
            number = int(prefix)
        text = re.sub(r'\x1b\[[0-9;]*m', '', raw)
        match = pattern.search(text)
        if not match:
            continue
        target, source, reason = match.groups()
        if target in edges:
            raise ValueError(f'duplicate first-enqueue target: {target}')
        edges[target] = dict(target=target, source=source, reason=reason, line=number,
                             raw=raw, text=text)
    cursor = args.target
    path = []
    seen = set()
    while cursor != args.start:
        if cursor in seen:
            raise ValueError('cycle in first-enqueue ancestry')
        seen.add(cursor)
        edge = edges[cursor]
        path.append(edge)
        cursor = edge['source']
    path.reverse()
    result = dict(input=str(args.input), numbered_input=args.numbered,
                  start=args.start, target=args.target,
                  first_discovery_edges_in_input=len(edges),
                  reason_counts_in_input=dict(Counter(e['reason'] for e in edges.values())),
                  path=path,
                  semantics='First-enqueue ancestry only; not a dynamic execution trace or complete call graph.')
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(path_edges=len(path), first_discovery_edges_in_input=len(edges),
                          output=str(args.output))))


if __name__ == '__main__':
    main()
