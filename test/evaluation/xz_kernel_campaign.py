#!/usr/bin/env python3
"""Retired XZ-only campaign: use test/section63/scripts/campaign.py."""

def analyze(*args, **kwargs):
    raise RuntimeError("The XZ-only replacement campaign is retired; use test/section63/scripts/analyze.py on the six-version campaign.")

if __name__ == '__main__':
    raise SystemExit("Use test/section63/scripts/campaign.py; XZ now shares the full three-algorithm protocol.")
