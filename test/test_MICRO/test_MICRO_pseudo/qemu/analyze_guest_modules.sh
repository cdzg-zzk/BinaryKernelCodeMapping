#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/work}"
TARGET="${1:-all}"

require_dir() {
	local path="$1"
	if [[ ! -d "${path}" ]]; then
		echo "missing required directory: ${path}" >&2
		exit 1
	fi
}

prepare_module_tree() {
	local module_dir="$1"

	rm -rf "${module_dir}"
	mkdir -p "${module_dir}"
	cp "${PROJECT_DIR}/kernel/Makefile" "${module_dir}/"
	cp "${PROJECT_DIR}/kernel/micro.c" "${module_dir}/"
	cp "${PROJECT_DIR}/kernel/micro.h" "${module_dir}/"
	cp "${PROJECT_DIR}/kernel/micro_pseudo.c" "${module_dir}/"
	cp "${PROJECT_DIR}/kernel/micro_pseudo.h" "${module_dir}/"
}

analyze_variant() {
	local variant="$1"
	local build_dir="${WORK_DIR}/build-${variant}"
	local module_dir="${WORK_DIR}/module-analyze-${variant}"

	require_dir "${build_dir}"
	prepare_module_tree "${module_dir}"

	make -C "${module_dir}" KDIR="${build_dir}" analyze
	echo "analyzed guest modules for ${variant}: ${module_dir}"
}

"${ROOT_DIR}/build_guest_kernels.sh"

case "${TARGET}" in
	retpoline|noretpoline)
		analyze_variant "${TARGET}"
		;;
	all)
		analyze_variant retpoline
		analyze_variant noretpoline
		;;
	*)
		echo "usage: $0 [retpoline|noretpoline|all]" >&2
		exit 1
		;;
esac
