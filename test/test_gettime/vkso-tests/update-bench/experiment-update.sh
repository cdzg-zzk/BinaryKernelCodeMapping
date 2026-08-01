#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0

set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
ARTIFACTS=$HERE/../baremetal/artifacts
NORMAL_PACKAGE=${NORMAL_PACKAGE:-$ARTIFACTS/final-update-normal}
NO_RETPOLINE_PACKAGE=${NO_RETPOLINE_PACKAGE:-$ARTIFACTS/final-update-no-retpoline}
RESULTS_DIR=${RESULTS_DIR:-$HERE/results}
EXPERIMENT_SCOPE=${EXPERIMENT_SCOPE:-update-side}
case "$EXPERIMENT_SCOPE" in
update-side)
	CONFIG_DEFAULT=$HERE/update-experiment.conf
	STATE_DEFAULT=$HERE/.update-experiment-state
	PEER_STATE_DEFAULT=$HERE/.concurrent-experiment-state
	RUN_SUFFIX=update-side-final
	COLLECTOR=collect-update-side.sh
	COMMAND_NAME=${EXPERIMENT_COMMAND:-./experiment-update.sh}
	;;
concurrent)
	CONFIG_DEFAULT=$HERE/concurrent-experiment.conf
	STATE_DEFAULT=$HERE/.concurrent-experiment-state
	PEER_STATE_DEFAULT=$HERE/.update-experiment-state
	RUN_SUFFIX=update-concurrent-final
	COLLECTOR=collect-update-concurrent.sh
	COMMAND_NAME=${EXPERIMENT_COMMAND:-./experiment-concurrent.sh}
	;;
*)
	echo "EXPERIMENT_SCOPE must be update-side or concurrent" >&2
	exit 2
	;;
esac
CONFIG=${CONFIG_FILE:-$CONFIG_DEFAULT}
STATE=${STATE_FILE:-$STATE_DEFAULT}
PEER_STATE=${PEER_STATE_FILE:-$PEER_STATE_DEFAULT}
LOCK=${LOCK_FILE:-$HERE/.update-experiment.lock}
CASES=(raw-normal vkso-normal raw-no-retpoline vkso-no-retpoline)

if [[ $(id -u) -eq 0 ]]; then
	echo "run $COMMAND_NAME as the regular user, without sudo" >&2
	exit 1
fi
test -s "$CONFIG" || {
	echo "missing experiment configuration: $CONFIG" >&2
	exit 1
}

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
		echo "invalid update experiment case: $1" >&2
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
}

load_state()
{
	local case_order saved_normal saved_no_ret

	test -s "$STATE" || {
		echo "no $EXPERIMENT_SCOPE experiment; start with: $COMMAND_NAME boot raw-normal" >&2
		exit 1
	}
	run_id=$(manifest_value "$STATE" run_id)
	next_index=$(manifest_value "$STATE" next_index)
	state_status=$(manifest_value "$STATE" status)
	result_root=$RESULTS_DIR/$run_id
	test -s "$result_root/experiment-manifest.txt"
	case_order=$(manifest_value "$result_root/experiment-manifest.txt" case_order)
	read -r -a CASES <<<"$case_order"
	[[ ${#CASES[@]} -eq 4 ]]
	test "$(manifest_value "$result_root/experiment-manifest.txt" bench_scope)" = \
		"$EXPERIMENT_SCOPE" || {
		echo "experiment scope does not match $COMMAND_NAME" >&2
		exit 1
	}
	[[ "$next_index" =~ ^[0-9]+$ ]]
	((next_index <= ${#CASES[@]}))
	saved_normal=$(manifest_value \
		"$result_root/experiment-manifest.txt" normal_package)
	saved_no_ret=$(manifest_value \
		"$result_root/experiment-manifest.txt" no_retpoline_package)
	NORMAL_PACKAGE=$saved_normal
	NO_RETPOLINE_PACKAGE=$saved_no_ret
	test "$(manifest_value "$STATE" experiment_manifest_sha256)" = \
		"$(sha256sum "$result_root/experiment-manifest.txt" |
			awk '{print $1}')" || {
		echo "update experiment manifest changed after start" >&2
		exit 1
	}
}

verify_packages_quiet()
{
	local file

	"$HERE/verify-update-packages.sh" \
		"$NORMAL_PACKAGE" "$NO_RETPOLINE_PACKAGE" >/dev/null
	for file in experiment-update.sh experiment-concurrent.sh \
		boot-update-once.sh update-experiment.conf \
		concurrent-experiment.conf; do
		cmp -s "$HERE/$file" "$NORMAL_PACKAGE/$file" || {
			echo "local experiment control differs from package: $file" >&2
			exit 1
		}
	done
}

verify_repository_identity()
{
	local commit normal_commit no_ret_commit expected_patch current_patch
	local expected_source source

	commit=$(git -C "$ROOT" rev-parse HEAD)
	normal_commit=$(manifest_value \
		"$NORMAL_PACKAGE/boot-manifest.txt" git_commit)
	no_ret_commit=$(manifest_value \
		"$NO_RETPOLINE_PACKAGE/boot-manifest.txt" git_commit)
	test "$commit" = "$normal_commit"
	test "$commit" = "$no_ret_commit"
	expected_patch=$(manifest_value \
		"$NORMAL_PACKAGE/boot-manifest.txt" candidate_patch_sha256)
	current_patch=$(git -C "$ROOT" diff --binary --no-ext-diff HEAD -- |
		sha256sum | awk '{print $1}')
	test "$current_patch" = "$expected_patch" || {
		echo "Git worktree changed after update packages were built" >&2
		git -C "$ROOT" status --short >&2
		exit 1
	}
	expected_source=$(manifest_value \
		"$NORMAL_PACKAGE/boot-manifest.txt" vkso_source_tree_sha256)
	source=$("$HERE/../baremetal/source-tree-hash.sh" \
		"$ROOT/test/test_gettime/linux-5.15.198-vkso")
	test "$source" = "$expected_source" || {
		echo "current VKSO source does not match the update packages" >&2
		exit 1
	}
}

begin_experiment()
{
	local requested_run_id=${1:-}
	local run_id manifest config_sha normal_manifest_sha no_ret_manifest_sha

	verify_packages_quiet
	verify_repository_identity
	if [[ -s "$STATE" &&
	      $(manifest_value "$STATE" status) == active ]]; then
		echo "a $EXPERIMENT_SCOPE experiment is already active: $(manifest_value "$STATE" run_id)" >&2
		exit 1
	fi
	if [[ -s "$PEER_STATE" &&
	      $(manifest_value "$PEER_STATE" status) == active ]]; then
		echo "another update experiment is active: $(manifest_value "$PEER_STATE" run_id)" >&2
		exit 1
	fi
	run_id=${requested_run_id:-$(date -u +%Y%m%dT%H%M%SZ)-$RUN_SUFFIX}
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
	no_ret_manifest_sha=$(sha256sum \
		"$NO_RETPOLINE_PACKAGE/boot-manifest.txt" | awk '{print $1}')
	# shellcheck disable=SC1090
	source "$CONFIG"
	test "$BENCH_SCOPE" = "$EXPERIMENT_SCOPE"
	{
		date -u '+created_utc=%Y-%m-%dT%H:%M:%SZ'
		printf 'run_id=%s\n' "$run_id"
		printf 'experiment_schema=%s\n' "$UPDATE_EXPERIMENT_SCHEMA"
		printf 'experiment_driver=%s\n' "$COMMAND_NAME"
		printf 'case_order=%s\n' "${CASES[*]}"
		printf 'git_commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD)"
		printf 'experiment_config_sha256=%s\n' "$config_sha"
		printf 'normal_package=%s\n' "$(realpath "$NORMAL_PACKAGE")"
		printf 'no_retpoline_package=%s\n' \
			"$(realpath "$NO_RETPOLINE_PACKAGE")"
		printf 'normal_manifest_sha256=%s\n' "$normal_manifest_sha"
		printf 'no_retpoline_manifest_sha256=%s\n' "$no_ret_manifest_sha"
		printf 'test_binary_sha256=%s\n' \
			"$(sha256sum "$NORMAL_PACKAGE/vkso-time-bench" |
				awk '{print $1}')"
		printf 'bench_scope=%s\n' "$BENCH_SCOPE"
		printf 'cpu=%s\n' "$CPU"
		printf 'housekeeping_cpus=%s\n' "$HOUSEKEEPING_CPUS"
		printf 'repeats=%s\n' "$REPEATS"
		printf 'update_seconds=%s\n' "$UPDATE_SECONDS"
		printf 'reader_iterations=%s\n' "$READER_ITERATIONS"
		printf 'warmup=%s\n' "$WARMUP"
		printf 'seq_iterations=%s\n' "$SEQ_ITERATIONS"
		printf 'stabilize_seconds=%s\n' "$STABILIZE_SECONDS"
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
		echo "update experiment is not active: $state_status" >&2
		exit 1
	}
	test "$next_index" -lt "${#CASES[@]}" || {
		echo "all update experiment cases are complete" >&2
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
	verify_repository_identity
	package=$(package_for_case "$expected")
	backend=${expected%%-*}
	image=/boot/vkso-update-$expected-5.15.198.bzImage
	test -s "$image" || {
		echo "update image is not installed: $image" >&2
		exit 1
	}
	package_hash=$(sha256sum "$package/$backend-bzImage" | awk '{print $1}')
	test "$(sha256sum "$image" | awk '{print $1}')" = "$package_hash" || {
		echo "installed update image does not match package: $image" >&2
		exit 1
	}
	"$HERE/boot-update-once.sh" "$expected"
}

boot_or_begin_case()
{
	local requested=${1:-} saved_status

	if [[ -s "$STATE" ]]; then
		saved_status=$(manifest_value "$STATE" status)
	else
		saved_status=not-started
	fi
	if [[ "$saved_status" != active ]]; then
		if [[ -n "$requested" && "$requested" != raw-normal ]]; then
			echo "a new update experiment must start with raw-normal" >&2
			exit 1
		fi
		begin_experiment ""
	fi
	boot_case "$requested"
}

collect_case()
{
	local requested=${1:-} expected package backend variant next archive temporary
	local complete_marker

	set_expected_case
	expected=$current_case
	if [[ -n "$requested" && "$requested" != "$expected" ]]; then
		echo "case order mismatch: expected $expected, requested $requested" >&2
		exit 1
	fi
	verify_packages_quiet
	verify_repository_identity
	package=$(package_for_case "$expected")
	backend=${expected%%-*}
	variant=${expected#*-}
	complete_marker=$result_root/$variant/$backend/complete
	# shellcheck disable=SC1090
	source "$CONFIG"
	if [[ ! -f "$complete_marker" ]]; then
		PACKAGE="$package" CONTROL_DIR="$HERE" RESULTS_DIR="$result_root" \
			RESULT_OWNER_ROOT="$result_root" \
			STATE_FILE="$result_root/.collector-$variant-$EXPERIMENT_SCOPE-state" \
			CPU="$CPU" REPEATS="$REPEATS" \
			UPDATE_SECONDS="$UPDATE_SECONDS" \
			READER_ITERATIONS="$READER_ITERATIONS" \
			WARMUP="$WARMUP" SEQ_ITERATIONS="$SEQ_ITERATIONS" \
			STABILIZE_SECONDS="$STABILIZE_SECONDS" \
			"$package/$COLLECTOR" "$variant"
	fi
	test -f "$complete_marker"
	next=$((next_index + 1))
	if [[ "$next" -lt "${#CASES[@]}" ]]; then
		write_state "$run_id" "$next" active
		echo "next_case=${CASES[$next]}"
	else
		archive=$RESULTS_DIR/$run_id.tar.gz
		temporary=$archive.partial.$$
		if ! tar -C "$RESULTS_DIR" -czf "$temporary" "$run_id"; then
			rm -f "$temporary"
			echo "result archive failed; rerun collect $expected to retry" >&2
			exit 1
		fi
		mv "$temporary" "$archive"
		sha256sum "$archive" >"$archive.sha256"
		write_state "$run_id" "$next" complete
		echo "experiment_complete=$run_id"
		echo "raw_data_archive=$archive"
	fi
	echo "result_root=$result_root"
}

show_status()
{
	local archive

	if [[ ! -s "$STATE" ]]; then
		echo "status=not-started"
		return
	fi
	load_state
	echo "run_id=$run_id"
	echo "bench_scope=$EXPERIMENT_SCOPE"
	echo "status=$state_status"
	echo "completed_cases=$next_index"
	if [[ "$state_status" == active &&
	      "$next_index" -lt "${#CASES[@]}" ]]; then
		echo "next_case=${CASES[$next_index]}"
	fi
	echo "result_root=$result_root"
	if [[ "$state_status" == complete ]]; then
		archive=$RESULTS_DIR/$run_id.tar.gz
		echo "raw_data_archive=$archive"
		if [[ -s "$archive" && -s "$archive.sha256" ]] &&
		   sha256sum -c "$archive.sha256" >/dev/null 2>&1; then
			echo "archive_status=complete"
		else
			echo "archive_status=missing-or-invalid"
		fi
	fi
}

mkdir -p "$RESULTS_DIR"
exec 9>"$LOCK"
flock -n 9 || {
	echo "another update experiment command is running" >&2
	exit 1
}

case "${1:-}" in
begin)
	begin_experiment "${2:-}"
	;;
boot)
	boot_or_begin_case "${2:-}"
	;;
collect)
	collect_case "${2:-}"
	;;
status)
	show_status
	;;
*)
	echo "usage: $COMMAND_NAME {begin [RUN_ID]|boot [CASE]|collect [CASE]|status}" >&2
	exit 2
	;;
esac
