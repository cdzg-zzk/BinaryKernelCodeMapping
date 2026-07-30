#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$HERE/artifacts/final-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$HERE/artifacts/final-no-retpoline}
RESULTS_DIR=${RESULTS_DIR:-$HERE/results}
STATE=${STATE_FILE:-$HERE/.experiment-state}
LOCK=${LOCK_FILE:-$HERE/.experiment.lock}
CONFIG=$HERE/experiment.conf
FULL_CASES=(raw-normal vkso-normal raw-no-retpoline vkso-no-retpoline)
NORMAL_CASES=(raw-normal vkso-normal)
CASES=("${FULL_CASES[@]}")

manifest_value()
{
	local file=$1 key=$2

	awk -F= -v key="$key" '$1 == key {
		sub(/^[^=]*=/, ""); print; exit
	}' "$file"
}

package_for_case()
{
	case "$1" in
	raw-normal|vkso-normal)
		printf '%s\n' "$NORMAL_PACKAGE"
		;;
	raw-no-retpoline|vkso-no-retpoline)
		printf '%s\n' "$NO_RETPOLINE_PACKAGE"
		;;
	*)
		echo "invalid experiment case: $1" >&2
		exit 2
		;;
	esac
}

write_state()
{
	local run_id=$1 next_index=$2 status=$3
	local temporary=$STATE.tmp.$$

	{
		printf 'run_id=%s\n' "$run_id"
		printf 'next_index=%s\n' "$next_index"
		printf 'status=%s\n' "$status"
		printf 'experiment_manifest_sha256=%s\n' \
			"$(sha256sum "$RESULTS_DIR/$run_id/experiment-manifest.txt" |
				awk '{print $1}')"
	} >"$temporary"
	chmod 0664 "$temporary"
	mv "$temporary" "$STATE"
	if [[ -n ${SUDO_UID:-} && -n ${SUDO_GID:-} ]]; then
		chown "$SUDO_UID:$SUDO_GID" "$STATE"
	fi
}

load_state()
{
	local case_order saved_normal saved_no_ret

	test -s "$STATE" || {
		echo "no active experiment; run: ./experiment.sh begin" >&2
		exit 1
	}
	run_id=$(manifest_value "$STATE" run_id)
	next_index=$(manifest_value "$STATE" next_index)
	state_status=$(manifest_value "$STATE" status)
	result_root=$RESULTS_DIR/$run_id
	test -s "$result_root/experiment-manifest.txt"
	case_order=$(manifest_value \
		"$result_root/experiment-manifest.txt" case_order)
	read -r -a CASES <<<"$case_order"
	[[ ${#CASES[@]} -eq 2 || ${#CASES[@]} -eq 4 ]]
	[[ "$next_index" =~ ^[0-9]+$ ]]
	((next_index <= ${#CASES[@]}))
	saved_normal=$(manifest_value \
		"$result_root/experiment-manifest.txt" normal_package)
	saved_no_ret=$(manifest_value \
		"$result_root/experiment-manifest.txt" no_retpoline_package)
	NORMAL_PACKAGE=$saved_normal
	if [[ "$saved_no_ret" != none ]]; then
		NO_RETPOLINE_PACKAGE=$saved_no_ret
	fi
	test "$(manifest_value "$STATE" experiment_manifest_sha256)" = \
		"$(sha256sum "$result_root/experiment-manifest.txt" |
			awk '{print $1}')" || {
		echo "experiment manifest changed after begin" >&2
		exit 1
	}
}

uses_no_retpoline()
{
	[[ " ${CASES[*]} " == *" raw-no-retpoline "* ]]
}

verify_packages_quiet()
{
	if uses_no_retpoline; then
		"$HERE/verify-packages.sh" \
			"$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" >/dev/null
	else
		(
			cd "$NORMAL_PACKAGE"
			sha256sum -c SHA256SUMS >/dev/null
		)
		test "$(manifest_value \
			"$NORMAL_PACKAGE/boot-manifest.txt" build_variant)" = normal
		test "$(manifest_value \
			"$NORMAL_PACKAGE/boot-manifest.txt" vkso_validation_tests)" = 0
	fi
}

verify_repository_identity()
{
	local commit normal_commit no_retpoline_commit expected_source source

	if [[ -n $(git -C "$ROOT" status --porcelain) ]]; then
		echo "Git worktree changed after final package construction" >&2
		git -C "$ROOT" status --short >&2
		exit 1
	fi
	commit=$(git -C "$ROOT" rev-parse HEAD)
	normal_commit=$(manifest_value \
		"$NORMAL_PACKAGE/boot-manifest.txt" git_commit)
	test "$commit" = "$normal_commit"
	if uses_no_retpoline; then
		no_retpoline_commit=$(manifest_value \
			"$NO_RETPOLINE_PACKAGE/boot-manifest.txt" git_commit)
		test "$commit" = "$no_retpoline_commit"
	fi

	expected_source=$(manifest_value \
		"$NORMAL_PACKAGE/boot-manifest.txt" vkso_source_tree_sha256)
	source=$("$HERE/source-tree-hash.sh" \
		"$ROOT/test/test_gettime/linux-5.15.198-vkso")
	test "$source" = "$expected_source" || {
		echo "current VKSO source does not match the final package" >&2
		exit 1
	}
}

begin_experiment()
{
	local requested_run_id=${1:-} mode=${2:-full}
	local run_id manifest config_sha normal_manifest_sha no_ret_manifest_sha

	case "$mode" in
	full)
		CASES=("${FULL_CASES[@]}")
		;;
	normal)
		CASES=("${NORMAL_CASES[@]}")
		;;
	*)
		echo "invalid experiment mode: $mode" >&2
		exit 2
		;;
	esac
	verify_packages_quiet
	verify_repository_identity
	if [[ -s "$STATE" &&
	      $(manifest_value "$STATE" status) == active ]]; then
		echo "an experiment is already active: $(manifest_value "$STATE" run_id)" >&2
		exit 1
	fi
	run_id=${requested_run_id:-$(date -u +%Y%m%dT%H%M%SZ)-vkso-final}
	[[ "$run_id" =~ ^[A-Za-z0-9._-]+$ ]] || {
		echo "run ID contains unsupported characters: $run_id" >&2
		exit 2
	}
	result_root=$RESULTS_DIR/$run_id
	[[ ! -e "$result_root" && ! -e "$RESULTS_DIR/$run_id.tar.gz" ]] || {
		echo "result path already exists: $result_root" >&2
		exit 1
	}
	mkdir -p "$result_root"
	manifest=$result_root/experiment-manifest.txt
	config_sha=$(sha256sum "$CONFIG" | awk '{print $1}')
	normal_manifest_sha=$(sha256sum \
		"$NORMAL_PACKAGE/boot-manifest.txt" | awk '{print $1}')
	if uses_no_retpoline; then
		no_ret_manifest_sha=$(sha256sum \
			"$NO_RETPOLINE_PACKAGE/boot-manifest.txt" | awk '{print $1}')
	else
		no_ret_manifest_sha=none
	fi
	# shellcheck disable=SC1090
	source "$CONFIG"
	{
		date -u '+created_utc=%Y-%m-%dT%H:%M:%SZ'
		printf 'run_id=%s\n' "$run_id"
		printf 'experiment_schema=%s\n' "$EXPERIMENT_SCHEMA"
		printf 'case_order=%s\n' "${CASES[*]}"
		printf 'git_commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
		printf 'experiment_config_sha256=%s\n' "$config_sha"
		printf 'normal_package=%s\n' "$(realpath "$NORMAL_PACKAGE")"
		if uses_no_retpoline; then
			printf 'no_retpoline_package=%s\n' \
				"$(realpath "$NO_RETPOLINE_PACKAGE")"
		else
			printf 'no_retpoline_package=none\n'
		fi
		printf 'normal_manifest_sha256=%s\n' "$normal_manifest_sha"
		printf 'no_retpoline_manifest_sha256=%s\n' \
			"$no_ret_manifest_sha"
		printf 'test_binary_sha256=%s\n' \
			"$(sha256sum "$NORMAL_PACKAGE/vkso-time-bench" |
				awk '{print $1}')"
		printf 'cpu=%s\n' "$CPU"
		printf 'housekeeping_cpus=%s\n' "$HOUSEKEEPING_CPUS"
		printf 'iterations=%s\n' "$ITERATIONS"
		printf 'repeats=%s\n' "$REPEATS"
		printf 'warmup=%s\n' "$WARMUP"
		printf 'pmu=%s\n' "$PMU"
		printf 'seq_iterations=%s\n' "$SEQ_ITERATIONS"
		printf 'raw_data_only=1\n'
		printf 'old_results_reused=0\n'
	} >"$manifest"
	write_state "$run_id" 0 active
	echo "experiment_started=$run_id"
	echo "next_case=${CASES[0]}"
}

set_expected_case()
{
	load_state
	test "$state_status" = active || {
		echo "experiment is not active: $state_status" >&2
		exit 1
	}
	test "$next_index" -lt "${#CASES[@]}" || {
		echo "all experiment cases are already complete" >&2
		exit 1
	}
	current_case=${CASES[$next_index]}
}

boot_case()
{
	local requested=${1:-} expected package backend image package_hash

	set_expected_case
	expected=$current_case
	if [[ -n "$requested" && "$requested" != "$expected" ]]; then
		echo "case order mismatch: expected $expected, requested $requested" >&2
		exit 1
	fi
	verify_packages_quiet
	package=$(package_for_case "$expected")
	backend=${expected%%-*}
	case "$expected" in
	*-normal)
		image=/boot/vkso-final-$backend-normal-5.15.198.bzImage
		;;
	*)
		image=/boot/vkso-final-$backend-no-retpoline-5.15.198.bzImage
		;;
	esac
	test -s "$image" || {
		echo "final image is not installed: $image" >&2
		exit 1
	}
	package_hash=$(sha256sum "$package/$backend-bzImage" | awk '{print $1}')
	test "$(sha256sum "$image" | awk '{print $1}')" = "$package_hash" || {
		echo "installed image does not match final package: $image" >&2
		exit 1
	}
	"$HERE/boot-once.sh" "$expected"
}

collect_case()
{
	local requested=${1:-} expected next archive temporary

	set_expected_case
	expected=$current_case
	if [[ -n "$requested" && "$requested" != "$expected" ]]; then
		echo "case order mismatch: expected $expected, requested $requested" >&2
		exit 1
	fi
	NORMAL_PACKAGE="$NORMAL_PACKAGE" \
		NO_RETPOLINE_PACKAGE="$NO_RETPOLINE_PACKAGE" \
		RESULTS_DIR="$RESULTS_DIR" STATE_FILE="$STATE" \
		"$HERE/collect-case.sh" "$expected" "$run_id"
	test -f "$result_root/$expected/complete"
	next=$((next_index + 1))
	if [[ "$next" -lt "${#CASES[@]}" ]]; then
		write_state "$run_id" "$next" active
		echo "next_case=${CASES[$next]}"
	else
		write_state "$run_id" "$next" complete
		archive=$RESULTS_DIR/$run_id.tar.gz
		temporary=$archive.partial.$$
		tar -C "$RESULTS_DIR" -czf "$temporary" "$run_id"
		mv "$temporary" "$archive"
		sha256sum "$archive" >"$archive.sha256"
		echo "experiment_complete=$run_id"
		echo "raw_data_archive=$archive"
	fi
}

show_status()
{
	if [[ ! -s "$STATE" ]]; then
		echo "status=not-started"
		return
	fi
	load_state
	echo "run_id=$run_id"
	echo "status=$state_status"
	echo "completed_cases=$next_index"
	if [[ "$state_status" == active &&
	      "$next_index" -lt "${#CASES[@]}" ]]; then
		echo "next_case=${CASES[$next_index]}"
	fi
	echo "result_root=$result_root"
}

mkdir -p "$RESULTS_DIR"
exec 9>"$LOCK"
flock -n 9 || {
	echo "another experiment command is running" >&2
	exit 1
}

case "${1:-}" in
begin)
	begin_experiment "${2:-}" full
	;;
begin-normal)
	begin_experiment "${2:-}" normal
	;;
boot)
	boot_case "${2:-}"
	;;
collect)
	collect_case "${2:-}"
	;;
status)
	show_status
	;;
*)
	echo "usage: $0 {begin [RUN_ID]|begin-normal [RUN_ID]|boot [CASE]|collect [CASE]|status}" >&2
	exit 2
	;;
esac
