#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/work}"
RESULT_ROOT="${RESULT_DIR_OVERRIDE:-${PROJECT_DIR}/results/crc32_le/$(date -u +%Y%m%dT%H%M%SZ)_qemu}"
OUTER_REPEATS="${OUTER_REPEATS:-5}"
WARMUP="${WARMUP:-3}"
REPEAT="${REPEAT:-9}"
SEED="${SEED:-0x1234}"
BATCH_ITERS="${BATCH_ITERS:-8192}"
INPUT_LEN="${INPUT_LEN:-256}"
TARGET_CALLS="${TARGET_CALLS:-200000}"
QEMU_MEM_MB="${QEMU_MEM_MB:-2048}"
QEMU_SMP="${QEMU_SMP:-1}"
GUEST_APPEND_EXTRA="${GUEST_APPEND_EXTRA:-nmi_watchdog=0 nowatchdog audit=0 page_alloc.shuffle=0 random.trust_cpu=on tsc=reliable clocksource=tsc}"

pick_qemu_machine() {
	if [[ -n "${QEMU_MACHINE:-}" ]]; then
		echo "${QEMU_MACHINE}"
		return
	fi

	if [[ -w /dev/kvm ]]; then
		echo "q35,accel=kvm"
	else
		echo "q35,accel=tcg"
	fi
}

pick_qemu_cpu() {
	if [[ -n "${QEMU_CPU:-}" ]]; then
		echo "${QEMU_CPU}"
		return
	fi

	if [[ "${QEMU_MACHINE_RESOLVED}" == *"accel=kvm"* ]]; then
		echo "host"
	else
		echo "max"
	fi
}

pick_host_cpu() {
	local raw part last=""

	if [[ -r /sys/devices/system/cpu/isolated ]]; then
		raw="$(cat /sys/devices/system/cpu/isolated)"
		for part in ${raw//,/ }; do
			if [[ "${part}" == *-* ]]; then
				last="${part##*-}"
			elif [[ -n "${part}" ]]; then
				last="${part}"
			fi
		done
	fi

	echo "${last:-0}"
}

HOST_CPU="${HOST_CPU:-$(pick_host_cpu)}"
QEMU_MACHINE_RESOLVED="$(pick_qemu_machine)"
QEMU_CPU_RESOLVED="$(pick_qemu_cpu)"

"${ROOT_DIR}/build_guest_kernels.sh"
"${ROOT_DIR}/build_guest_initramfs.sh" retpoline
"${ROOT_DIR}/build_guest_initramfs.sh" noretpoline

mkdir -p "${RESULT_ROOT}"

run_guest() {
	local flavor="$1"
	local subdir="${RESULT_ROOT}/${flavor}"
	local serial_log="${subdir}/serial.log"
	local kernel_image="${WORK_DIR}/build-${flavor}/arch/x86/boot/bzImage"
	local initramfs="${WORK_DIR}/initramfs-${flavor}.cpio.gz"
	local append="console=ttyS0 rdinit=/init panic=-1 outer_repeats=${OUTER_REPEATS} warmup=${WARMUP} repeat=${REPEAT} seed=${SEED} batch_iters=${BATCH_ITERS} input_len=${INPUT_LEN} target_calls=${TARGET_CALLS}"

	mkdir -p "${subdir}"
	cat > "${subdir}/run_env.txt" <<EOF
flavor=${flavor}
benchmark=crc32_le
outer_repeats=${OUTER_REPEATS}
warmup=${WARMUP}
repeat=${REPEAT}
seed=${SEED}
batch_iters=${BATCH_ITERS}
input_len=${INPUT_LEN}
target_calls=${TARGET_CALLS}
qemu_machine=${QEMU_MACHINE_RESOLVED}
qemu_cpu=${QEMU_CPU_RESOLVED}
qemu_mem_mb=${QEMU_MEM_MB}
qemu_smp=${QEMU_SMP}
host_cpu=${HOST_CPU}
guest_append_extra=${GUEST_APPEND_EXTRA}
timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

	taskset -c "${HOST_CPU}" qemu-system-x86_64 \
		-machine "${QEMU_MACHINE_RESOLVED}" \
		-cpu "${QEMU_CPU_RESOLVED}" \
		-m "${QEMU_MEM_MB}" \
		-smp "${QEMU_SMP}" \
		-kernel "${kernel_image}" \
		-initrd "${initramfs}" \
		-append "${append} ${GUEST_APPEND_EXTRA}" \
		-nographic \
		-nodefaults \
		-no-user-config \
		-net none \
		-no-reboot \
		-monitor none \
		-serial "file:${serial_log}"

	python3 "${ROOT_DIR}/parse_qemu_serial.py" "${serial_log}" "${subdir}"
}

run_guest retpoline
run_guest noretpoline
echo "results written to ${RESULT_ROOT}"
