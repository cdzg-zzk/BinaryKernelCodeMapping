#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD=${BUILD:-/tmp/vkso-m24-build}
WORK=${WORK:-/tmp/vkso-m24-run}
TIME_WORK="$WORK/time"
GETCPU_WORK="$WORK/getcpu"
RESULT="$GETCPU_WORK/qemu.log"
QEMU_SMP=${QEMU_SMP:-4,sockets=2,cores=2,threads=1}
QEMU_TCG_THREAD=${QEMU_TCG_THREAD:-single}
QEMU_EXTRA_ARGS=${QEMU_EXTRA_ARGS:--object memory-backend-ram,size=256M,id=node0mem -object memory-backend-ram,size=256M,id=node1mem -numa node,nodeid=0,cpus=0-1,memdev=node0mem -numa node,nodeid=1,cpus=2-3,memdev=node1mem}

BUILD="$BUILD" WORK="$TIME_WORK" "$SCRIPT_DIR/../m23/run.sh"

BUILD="$BUILD" WORK="$GETCPU_WORK" GETCPU_ONLY=1 QEMU_SMP="$QEMU_SMP" \
	QEMU_TCG_THREAD="$QEMU_TCG_THREAD" \
	QEMU_EXTRA_ARGS="$QEMU_EXTRA_ARGS" "$SCRIPT_DIR/../m04/run.sh"

disassembly=$(objdump -d --disassemble=__vkso_getcpu "$BUILD/vmlinux")
if grep -Eq '[[:space:]]call[q]?[[:space:]]|[[:space:]]jmp[q]?[[:space:]]+\*' \
	<<<"$disassembly"; then
	echo "M24 getcpu contains a call or indirect jump" >&2
	exit 1
fi
if ! grep -Eq '[[:space:]](lsl|rdpid)[[:space:]]' <<<"$disassembly"; then
	echo "M24 getcpu lacks an x86 CPU/node read instruction" >&2
	exit 1
fi

for marker in \
	"kernel_getcpu_cpu=pass samples_per_cpu=10000" \
	"kernel_getcpu_node=pass nodes=2 samples_per_cpu=10000" \
	"kernel_getcpu_null=pass combinations=4" \
	"kernel_getcpu_multi_cpu=pass cpus=4 samples_per_cpu=10000" \
	"user_getcpu_cpu=pass samples_per_cpu=10000" \
	"user_getcpu_node=pass nodes=2 samples_per_cpu=10000" \
	"user_getcpu_null=pass combinations=4" \
	"user_getcpu_multi_cpu=pass cpus=4 samples_per_cpu=10000" \
	"user_getcpu_multithread=pass threads=4 samples_per_thread=10000"; do
	grep -Fq "$marker" "$RESULT" || {
		echo "missing M24 marker: $marker" >&2
		exit 1
	}
done

echo "M24 static PASS: inline CPU/node read without calls"
echo "M24 PASS: $RESULT"
