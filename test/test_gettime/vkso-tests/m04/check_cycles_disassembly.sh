#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

BUILD=$1
SYMBOL=$2
LABEL=$3

disassembly=$(objdump -d --disassemble="$SYMBOL" "$BUILD/vmlinux")

grep -Eq '[[:space:]]rdtsc(p)?[[:space:]]*$' <<<"$disassembly" || {
	echo "$LABEL: inline TSC instruction missing" >&2
	exit 1
}
if grep -Eq '[[:space:]](call|jmp)[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "$LABEL: indirect call/jump found" >&2
	exit 1
fi
unexpected_calls=$(grep -E '[[:space:]]call[q]?[[:space:]]' \
	<<<"$disassembly" |
	grep -Ev '<vkso_read_(pvclock|hvclock)_cycles>$' || true)
if [[ -n "$unexpected_calls" ]]; then
	echo "$LABEL: call outside approved PV/HV cold paths" >&2
	echo "$unexpected_calls" >&2
	exit 1
fi
