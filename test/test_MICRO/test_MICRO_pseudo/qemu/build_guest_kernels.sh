#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/work}"
SRC_BUNDLE="${SRC_BUNDLE:-/usr/src/linux-source-5.15.0/linux-source-5.15.0.tar.bz2}"
SRC_DIR="${WORK_DIR}/src/linux-source-5.15.0"
BASE_DEFCONFIG="${BASE_DEFCONFIG:-x86_64_defconfig}"
COMMON_FRAGMENT="${COMMON_FRAGMENT:-${ROOT_DIR}/guest_kernel_common.config}"
JOBS="${JOBS:-$(nproc)}"

require_file() {
	local path="$1"
	if [[ ! -e "${path}" ]]; then
		echo "missing required file: ${path}" >&2
		exit 1
	fi
}

ensure_source() {
	require_file "${SRC_BUNDLE}"
	if [[ -d "${SRC_DIR}" ]]; then
		return
	fi
	mkdir -p "${WORK_DIR}/src"
	tar -xf "${SRC_BUNDLE}" -C "${WORK_DIR}/src"
}

ensure_guest_crc32_micro_overlay() {
	local builtin_src="${PROJECT_DIR}/kernel/crc32_micro_builtin.c"
	local guest_builtin="${SRC_DIR}/lib/crc32_micro.c"
	local guest_makefile="${SRC_DIR}/lib/Makefile"
	local guest_header="${SRC_DIR}/include/linux/crc32.h"

	require_file "${builtin_src}"
	cp "${builtin_src}" "${guest_builtin}"

	if ! grep -q '^obj-y[[:space:]]\+.*crc32_micro\.o' "${guest_makefile}"; then
		printf '\nobj-y += crc32_micro.o\n' >> "${guest_makefile}"
	fi

	if ! grep -q 'crc32_le_micro' "${guest_header}"; then
		python3 - "${guest_header}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
needle = "u32 __pure crc32_be(u32 crc, unsigned char const *p, size_t len);\n"
insert = needle + "u32 crc32_le_micro(u32 crc, unsigned char const *p, size_t len);\n"
if "crc32_le_micro" not in text:
    if needle not in text:
        raise SystemExit(f"failed to find insertion point in {path}")
    text = text.replace(needle, insert, 1)
    path.write_text(text)
PY
	fi
}

merge_configs() {
	(
		cd "${SRC_DIR}"
		./scripts/kconfig/merge_config.sh -O "$1" "$2" "$3" "$4"
	)
}

configure_variant() {
	local variant="$1"
	local build_dir="$2"
	local config_file="${build_dir}/.config"
	local variant_fragment="${build_dir}/variant-${variant}.config"

	rm -rf "${build_dir}"
	mkdir -p "${build_dir}"

	make -C "${SRC_DIR}" O="${build_dir}" "${BASE_DEFCONFIG}"
	require_file "${COMMON_FRAGMENT}"

	case "${variant}" in
		retpoline)
			cat > "${variant_fragment}" <<'EOF'
CONFIG_LOCALVERSION="-crc32-retpoline"
CONFIG_RETPOLINE=y
CONFIG_RETHUNK=y
EOF
			;;
		noretpoline)
			cat > "${variant_fragment}" <<'EOF'
CONFIG_LOCALVERSION="-crc32-noretpoline"
# CONFIG_RETPOLINE is not set
# CONFIG_RETHUNK is not set
EOF
			;;
		*)
			echo "unknown variant: ${variant}" >&2
			exit 1
			;;
	esac

	merge_configs "${build_dir}" "${config_file}" "${COMMON_FRAGMENT}" "${variant_fragment}"
}

build_variant() {
	local variant="$1"
	local build_dir="${WORK_DIR}/build-${variant}"

	if [[ "${REBUILD_KERNELS:-0}" != "1" && -f "${build_dir}/arch/x86/boot/bzImage" ]]; then
		echo "kernel ${variant} already built: ${build_dir}/arch/x86/boot/bzImage"
		return
	fi

	configure_variant "${variant}" "${build_dir}"
	make -C "${SRC_DIR}" O="${build_dir}" -j"${JOBS}" bzImage
	make -C "${SRC_DIR}" O="${build_dir}" modules_prepare
	echo "built ${variant} kernel: ${build_dir}/arch/x86/boot/bzImage"
}

main() {
	ensure_source
	ensure_guest_crc32_micro_overlay
	build_variant retpoline
	build_variant noretpoline
}

main "$@"
