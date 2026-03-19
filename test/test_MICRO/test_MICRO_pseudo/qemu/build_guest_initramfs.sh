#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/work}"
VARIANT="${1:?usage: build_guest_initramfs.sh <retpoline|noretpoline>}"
BUILD_DIR="${WORK_DIR}/build-${VARIANT}"
MODULE_BUILD_DIR="${WORK_DIR}/module-${VARIANT}"
INITRAMFS_DIR="${WORK_DIR}/initramfs-${VARIANT}"
OUT_FILE="${WORK_DIR}/initramfs-${VARIANT}.cpio.gz"
BUSYBOX_BIN="${BUSYBOX_BIN:-$(command -v busybox)}"
PERF_BIN="${PERF_BIN:-/usr/bin/perf}"

require_file() {
	local path="$1"
	if [[ ! -e "${path}" ]]; then
		echo "missing required file: ${path}" >&2
		exit 1
	fi
}

resolve_perf_bin() {
	local candidate="$1"
	local full_version_path="/usr/lib/linux-tools/$(uname -r)/perf"
	local version_no_flavor
	local legacy_path
	local first_match

	require_file "${candidate}"
	if file -L "${candidate}" | grep -qi 'shell script'; then
		if [[ -x "${full_version_path}" ]]; then
			echo "${full_version_path}"
			return
		fi

		version_no_flavor="$(uname -r)"
		version_no_flavor="${version_no_flavor%-*}"
		legacy_path="/usr/lib/linux-tools-${version_no_flavor}/perf"
		if [[ -x "${legacy_path}" ]]; then
			echo "${legacy_path}"
			return
		fi

		first_match="$(find /usr/lib -path '*/linux-tools/*/perf' -o -path '*/linux-tools-*/perf' | head -n 1)"
		if [[ -n "${first_match}" ]]; then
			echo "${first_match}"
			return
		fi
	fi

	echo "${candidate}"
}

copy_binary_with_libs() {
	local src="$1"
	local dst="$2"
	local lib

	mkdir -p "${INITRAMFS_DIR}$(dirname "${dst}")"
	cp -L "${src}" "${INITRAMFS_DIR}${dst}"

	if ! file -L "${src}" | grep -qi 'dynamically linked'; then
		return
	fi

	while read -r lib; do
		[[ -n "${lib}" ]] || continue
		mkdir -p "${INITRAMFS_DIR}$(dirname "${lib}")"
		cp -L "${lib}" "${INITRAMFS_DIR}${lib}"
	done < <(ldd "${src}" | awk '/=> \// { print $3 } /^[[:space:]]*\// { print $1 }')
}

if [[ ! -d "${BUILD_DIR}" ]]; then
	echo "guest build dir not found: ${BUILD_DIR}" >&2
	echo "run build_guest_kernels.sh first" >&2
	exit 1
fi

rm -rf "${MODULE_BUILD_DIR}" "${INITRAMFS_DIR}"
mkdir -p "${MODULE_BUILD_DIR}" "${INITRAMFS_DIR}"

cp "${PROJECT_DIR}/kernel/Makefile" "${MODULE_BUILD_DIR}/"
cp "${PROJECT_DIR}/kernel/micro.h" "${MODULE_BUILD_DIR}/"
cp "${PROJECT_DIR}/kernel/micro_pseudo.c" "${MODULE_BUILD_DIR}/"
cp "${PROJECT_DIR}/kernel/micro_pseudo.h" "${MODULE_BUILD_DIR}/"
make -C "${MODULE_BUILD_DIR}" KDIR="${BUILD_DIR}" clean >/dev/null 2>&1 || true
make -C "${MODULE_BUILD_DIR}" KDIR="${BUILD_DIR}"

mkdir -p "${INITRAMFS_DIR}/bin" \
	"${INITRAMFS_DIR}/sbin" \
	"${INITRAMFS_DIR}/usr/bin" \
	"${INITRAMFS_DIR}/proc" \
	"${INITRAMFS_DIR}/sys" \
	"${INITRAMFS_DIR}/dev" \
	"${INITRAMFS_DIR}/lib" \
	"${INITRAMFS_DIR}/lib64" \
	"${INITRAMFS_DIR}/tmp" \
	"${INITRAMFS_DIR}/root"

cp "${BUSYBOX_BIN}" "${INITRAMFS_DIR}/bin/busybox"
for applet in sh mount umount mkdir cat echo dmesg poweroff reboot uname grep sed awk sleep sync insmod modprobe ls chmod chown kill; do
	ln -sf /bin/busybox "${INITRAMFS_DIR}/bin/${applet}"
done

PERF_BIN="$(resolve_perf_bin "${PERF_BIN}")"
copy_binary_with_libs "${PERF_BIN}" "/usr/bin/perf"
cp "${MODULE_BUILD_DIR}/micro_pseudo.ko" "${INITRAMFS_DIR}/micro_pseudo.ko"
cp "${ROOT_DIR}/guest_init.sh" "${INITRAMFS_DIR}/init"
cp "${ROOT_DIR}/guest_runner.sh" "${INITRAMFS_DIR}/guest_runner.sh"
chmod +x "${INITRAMFS_DIR}/init" "${INITRAMFS_DIR}/guest_runner.sh"

(
	cd "${INITRAMFS_DIR}"
	find . -print0 | cpio --null -ov --format=newc | gzip -9 > "${OUT_FILE}"
)

echo "built initramfs: ${OUT_FILE}"
