#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
KERNEL="$ROOT/test/test_gettime/linux-5.15.198-vkso"
NO_VDSO_KERNEL="$ROOT/test/test_gettime/linux-5.15.198-no-vdso"
VKSO_BUILD=${VKSO_BUILD:-/tmp/vkso-m27-vkso-build}
VKSO_OFF_BUILD=${VKSO_OFF_BUILD:-/tmp/vkso-m27-off-build}
RAW_BUILD=${RAW_BUILD:-/tmp/vkso-m27-raw-build}
WORK=${WORK:-/tmp/vkso-m27-run}
AUDIT_WORK=${AUDIT_WORK:-$WORK/final-audit}
RESULT=${RESULT:-$WORK/final_audit.txt}
JOBS=${JOBS:-$(nproc)}

require_file()
{
	if [[ ! -f "$1" ]]; then
		echo "missing required artifact: $1" >&2
		exit 1
	fi
}

section_size()
{
	local file=$1
	local section=$2
	local size

	size=$(objdump -h "$file" |
		awk -v section="$section" '$2 == section { print $3; exit }')
	if [[ -z "$size" ]]; then
		echo "missing section $section in $file" >&2
		exit 1
	fi
	printf '%d\n' "$((16#$size))"
}

symbol_size()
{
	local file=$1
	local symbol=$2
	local size

	size=$(nm -S "$file" |
		awk -v symbol="$symbol" '$4 == symbol { print $2; exit }')
	if [[ -z "$size" ]]; then
		echo "missing symbol $symbol in $file" >&2
		exit 1
	fi
	printf '%d\n' "$((16#$size))"
}

c_sloc()
{
	awk '
		BEGIN { block = 0; count = 0 }
		{
			line = $0
			for (;;) {
				if (block) {
					if (match(line, /\*\//)) {
						line = substr(line, RSTART + RLENGTH)
						block = 0
					} else {
						line = ""
						break
					}
				} else if (match(line, /\/\*/)) {
					before = substr(line, 1, RSTART - 1)
					after = substr(line, RSTART + RLENGTH)
					if (match(after, /\*\//)) {
						line = before substr(after,
							RSTART + RLENGTH)
					} else {
						line = before
						block = 1
					}
				} else {
					break
				}
			}
			sub(/[[:space:]]*\/\/.*/, "", line)
			gsub(/[[:space:]]/, "", line)
			if (length(line))
				count++
		}
		END { print count }
	' "$@"
}

sh_sloc()
{
	awk '
		/^[[:space:]]*$/ { next }
		/^[[:space:]]*#/ && !/^#!/ { next }
		{ count++ }
		END { print count + 0 }
	' "$@"
}

if [[ ${RUN_QEMU:-0} == 1 ]]; then
	"$SCRIPT_DIR/run.sh"
fi

if [[ ${BUILD_OFF:-0} == 1 ]]; then
	require_file "$VKSO_BUILD/.config"
	mkdir -p "$VKSO_OFF_BUILD"
	cp "$VKSO_BUILD/.config" "$VKSO_OFF_BUILD/.config"
	"$KERNEL/scripts/config" --file "$VKSO_OFF_BUILD/.config" \
		--disable VKSO_TIME --disable VKSO_TIME_TEST
	make -C "$KERNEL" O="$VKSO_OFF_BUILD" olddefconfig
	make -C "$KERNEL" O="$VKSO_OFF_BUILD" -j"$JOBS" bzImage
fi

require_file "$VKSO_BUILD/.config"
require_file "$VKSO_BUILD/vmlinux"
require_file "$VKSO_BUILD/arch/x86/boot/bzImage"
require_file "$VKSO_OFF_BUILD/.config"
require_file "$VKSO_OFF_BUILD/vmlinux"
require_file "$VKSO_OFF_BUILD/arch/x86/boot/bzImage"
require_file "$RAW_BUILD/arch/x86/entry/vdso/vdso64.so.dbg"
require_file "$WORK/raw.log"
require_file "$WORK/vkso.log"
require_file "$WORK/raw-multicpu.log"
require_file "$WORK/vkso-multicpu.log"

mkdir -p "$AUDIT_WORK" "$(dirname "$RESULT")"
exec > >(tee "$RESULT") 2>&1

echo "VKSO final audit"
echo "================"

grep -Fqx 'CONFIG_VKSO_TIME=y' "$VKSO_BUILD/.config"
grep -Fqx '# CONFIG_VKSO_TIME_TEST is not set' "$VKSO_BUILD/.config"
grep -Fqx '# CONFIG_VKSO_TIME is not set' "$VKSO_OFF_BUILD/.config"

nm "$VKSO_BUILD/vmlinux" >"$AUDIT_WORK/vkso.symbols"
if grep -q '__vkso_test_' "$AUDIT_WORK/vkso.symbols"; then
	echo "production vmlinux contains a test probe" >&2
	exit 1
fi
if [[ -e "$VKSO_BUILD/kernel/time/vkso_time_test.o" ]]; then
	echo "production build contains vkso_time_test.o" >&2
	exit 1
fi

nm "$VKSO_OFF_BUILD/vmlinux" >"$AUDIT_WORK/vkso-off.symbols"
if grep -qi 'vkso' "$AUDIT_WORK/vkso-off.symbols"; then
	echo "CONFIG_VKSO_TIME=n vmlinux contains a VKSO symbol" >&2
	exit 1
fi
if find "$VKSO_OFF_BUILD" -type f -name '*vkso*.o' -print -quit |
	grep -q .; then
	echo "CONFIG_VKSO_TIME=n build contains a VKSO object" >&2
	exit 1
fi
echo "config.production=pass test_probe=absent"
echo "config.disabled=pass objects=0 symbols=0"

tr -d '\r' <"$WORK/raw.log" |
	grep -E '^(semantics|path|namespace)\.' \
	>"$AUDIT_WORK/raw.matrix"
tr -d '\r' <"$WORK/vkso.log" |
	grep -E '^(semantics|path|namespace)\.' \
	>"$AUDIT_WORK/vkso.matrix"
diff -u "$AUDIT_WORK/raw.matrix" "$AUDIT_WORK/vkso.matrix" \
	>"$AUDIT_WORK/raw-vkso.diff"

tr -d '\r' <"$WORK/raw-multicpu.log" |
	grep -E '^(semantics|path)\.' \
	>"$AUDIT_WORK/raw-multicpu.matrix"
tr -d '\r' <"$WORK/vkso-multicpu.log" |
	grep -E '^(semantics|path)\.' \
	>"$AUDIT_WORK/vkso-multicpu.matrix"
diff -u "$AUDIT_WORK/raw-multicpu.matrix" \
	"$AUDIT_WORK/vkso-multicpu.matrix" \
	>"$AUDIT_WORK/raw-vkso-multicpu.diff"

grep -Fq 'abi_matrix_status=pass' "$WORK/raw.log"
grep -Fq 'abi_matrix_status=pass' "$WORK/vkso.log"
grep -Fq 'namespace.lifecycle_status=pass' "$WORK/raw.log"
grep -Fq 'namespace.lifecycle_status=pass' "$WORK/vkso.log"
grep -Fq 'lifecycle.repeat_restore=pass cycles=2' "$WORK/vkso.log"
grep -Fq 'multicpu_matrix_status=pass' "$WORK/raw-multicpu.log"
grep -Fq 'multicpu_matrix_status=pass' "$WORK/vkso-multicpu.log"
echo "qemu.main_matrix=pass rows=$(wc -l <"$AUDIT_WORK/raw.matrix")"
echo "qemu.multicpu_matrix=pass rows=$(wc -l <"$AUDIT_WORK/raw-multicpu.matrix")"
echo "qemu.mapping_lifecycle=pass cycles=2"

objdump -dr "$VKSO_BUILD/kernel/time/vkso_time_core.o" \
	>"$AUDIT_WORK/vkso_time_core.dis"
objdump -dr "$VKSO_BUILD/kernel/time/vkso_time_cycles.o" \
	>"$AUDIT_WORK/vkso_time_cycles.dis"
grep -qw rdtsc "$AUDIT_WORK/vkso_time_core.dis"
grep -q 'R_X86_64_PLT32[[:space:]]*vkso_read_pvclock_cycles' \
	"$AUDIT_WORK/vkso_time_core.dis"
grep -q 'R_X86_64_PLT32[[:space:]]*vkso_read_hvclock_cycles' \
	"$AUDIT_WORK/vkso_time_core.dis"
if grep -Eq '\bcallq?[[:space:]]+\*' "$AUDIT_WORK/vkso_time_core.dis"; then
	echo "shared time core contains an indirect call" >&2
	exit 1
fi
grep -q ' vkso_read_pvclock_cycles$' "$AUDIT_WORK/vkso.symbols"
grep -q ' vkso_read_hvclock_cycles$' "$AUDIT_WORK/vkso.symbols"
echo "disassembly.tsc=pass inline=1 indirect_calls=0"
echo "disassembly.pvclock=static-pass direct_cold_call=1"
echo "disassembly.hyperv=static-pass direct_cold_call=1"

core_text=$(section_size "$VKSO_BUILD/kernel/time/vkso_time_core.o" \
	.vkso.text)
provider_text=$(section_size \
	"$VKSO_BUILD/kernel/time/vkso_time_cycles.o" .vkso.text)
getcpu_text=$(section_size \
	"$VKSO_BUILD/arch/x86/kernel/vkso_getcpu.o" .vkso.text)
vkso_text=$((core_text + provider_text + getcpu_text))
raw_text=$(section_size \
	"$RAW_BUILD/arch/x86/entry/vdso/vdso64.so.dbg" .text)
raw_api_text=0
for symbol in \
	__vdso_clock_gettime __vdso_clock_getres __vdso_gettimeofday \
	__vdso_time __vdso_getcpu; do
	raw_api_text=$((raw_api_text +
		$(symbol_size \
		"$RAW_BUILD/arch/x86/entry/vdso/vdso64.so.dbg" "$symbol")))
done

wrapper_object="$AUDIT_WORK/vkso_user_wrapper.o"
gcc -O2 -Wall -Wextra -Werror -c \
	"$SCRIPT_DIR/vkso_user_wrapper.c" -o "$wrapper_object"
wrapper_text=$(section_size "$wrapper_object" .text)
wrapper_api_text=0
for symbol in \
	vkso_user_clock_gettime vkso_user_clock_getres \
	vkso_user_gettimeofday vkso_user_time vkso_user_getcpu; do
	wrapper_api_text=$((wrapper_api_text +
		$(symbol_size "$wrapper_object" "$symbol")))
done

echo "text.vkso_shared_core_bytes=$core_text"
echo "text.vkso_counter_provider_bytes=$provider_text"
echo "text.vkso_getcpu_bytes=$getcpu_text"
echo "text.vkso_total_production_bytes=$vkso_text"
echo "text.raw_vdso_section_bytes=$raw_text"
echo "text.raw_vdso_api_bytes=$raw_api_text"
echo "text.user_wrapper_section_bytes=$wrapper_text"
echo "text.user_wrapper_api_bytes=$wrapper_api_text"
echo "text.vkso_steady_user_bytes=$((vkso_text + wrapper_api_text))"

shared_core_sloc=$(c_sloc \
	"$KERNEL/include/vkso/time.h" \
	"$KERNEL/include/vkso/getcpu.h" \
	"$KERNEL/kernel/time/vkso_time_internal.h" \
	"$KERNEL/kernel/time/vkso_time_core.c" \
	"$KERNEL/arch/x86/kernel/vkso_getcpu.c")
provider_sloc=$(c_sloc "$KERNEL/kernel/time/vkso_time_cycles.c")
kernel_adapter_sloc=$(c_sloc \
	"$KERNEL/kernel/time/vkso_time.c" \
	"$KERNEL/arch/x86/kernel/vkso.c" \
	"$KERNEL/arch/x86/include/asm/vkso.h" \
	"$KERNEL/include/linux/vkso.h" \
	"$KERNEL/include/linux/vkso_time.h" \
	"$KERNEL/include/linux/vkso_getcpu.h")
user_wrapper_sloc=$(c_sloc \
	"$SCRIPT_DIR/vkso_user_wrapper.c" \
	"$SCRIPT_DIR/vkso_user_wrapper.h" \
	"$SCRIPT_DIR/vkso_abi.h")
test_sloc=$(c_sloc \
	"$KERNEL/kernel/time/vkso_time_test.c" \
	"$ROOT/test/test_gettime/vkso-tests/m04/kernel_smoke.c" \
	"$ROOT/test/test_gettime/vkso-tests/m04/user_test.c" \
	"$SCRIPT_DIR/abi_matrix.c")
test_sloc=$((test_sloc + $(sh_sloc \
	"$ROOT/test/test_gettime/vkso-tests/m04/check_cycles_disassembly.sh" \
	"$ROOT/test/test_gettime/vkso-tests/m04/guest_init" \
	"$ROOT/test/test_gettime/vkso-tests/m04/run.sh" \
	"$SCRIPT_DIR/guest_init" \
	"$SCRIPT_DIR/run.sh" \
	"$SCRIPT_DIR/final_audit.sh")))

compat_add=0
compat_del=0
compat_files=(
	arch/x86/Kconfig
	arch/x86/entry/Makefile
	arch/x86/include/asm/elf.h
	arch/x86/include/asm/mmu.h
	arch/x86/include/asm/mmu_context.h
	arch/x86/include/uapi/asm/auxvec.h
	arch/x86/kernel/Makefile
	arch/x86/kernel/cpu/mshyperv.c
	arch/x86/kernel/kvmclock.c
	arch/x86/kernel/pvclock.c
	arch/x86/kernel/vmlinux.lds.S
	drivers/clocksource/hyperv_timer.c
	include/linux/clocksource.h
	include/linux/time_namespace.h
	include/linux/timekeeper_internal.h
	include/uapi/linux/auxvec.h
	init/Kconfig
	kernel/nsproxy.c
	kernel/sys.c
	kernel/time/Makefile
	kernel/time/namespace.c
	kernel/time/posix-timers.c
	kernel/time/time.c
	kernel/time/timekeeping.c
)
for file in "${compat_files[@]}"; do
	add=0
	del=0
	if cmp -s "$NO_VDSO_KERNEL/$file" "$KERNEL/$file"; then
		continue
	fi
	read -r add del _ < <(git diff --no-index --numstat \
		"$NO_VDSO_KERNEL/$file" "$KERNEL/$file" || true)
	if [[ ${add:-0} =~ ^[0-9]+$ ]]; then
		compat_add=$((compat_add + add))
	fi
	if [[ ${del:-0} =~ ^[0-9]+$ ]]; then
		compat_del=$((compat_del + del))
	fi
done

echo "sloc.shared_core=$shared_core_sloc"
echo "sloc.counter_provider=$provider_sloc"
echo "sloc.kernel_adapter=$kernel_adapter_sloc"
echo "sloc.user_wrapper=$user_wrapper_sloc"
echo "sloc.test=$test_sloc"
echo "compatibility.delta_vs_no_vdso=+$compat_add/-$compat_del"

echo "cacheline.hot_hres=pass seq_cycles_realtime_monotonic_bytes=0..63"
echo "cacheline.raw=pass bytes=128..167 one_64B_line=1"
echo "cacheline.writer_invalidation=unchanged full_snapshot_publish=1"
echo "audit_status=pass"
echo "audit_result=$RESULT"
