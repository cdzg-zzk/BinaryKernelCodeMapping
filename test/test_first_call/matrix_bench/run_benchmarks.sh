#!/usr/bin/env bash
set -euo pipefail

TARGETS=(native stub)
CONDITIONS=(${CONDITIONS_OVERRIDE:-hot pte-cold post-drop})

export STUB_DSO=${STUB_DSO:-$(realpath ../tmp/libzzk_xxh32_lkm.so)}
export NATIVE_DSO=${NATIVE_DSO:-$(realpath ../so/libclone_xxh32.so)}

for condition in "${CONDITIONS[@]}"; do
  if [ "$condition" = "post-drop" ] && [ "$EUID" -ne 0 ]; then
    echo "post-drop requires root because it writes /proc/sys/vm/drop_caches." >&2
    echo "Run with sudo, or set CONDITIONS_OVERRIDE='hot pte-cold'." >&2
    exit 1
  fi
done

NUM_RUNS=${NUM_RUNS:-100}
THRESHOLD_PCT=${THRESHOLD_PCT:-90.0}
TARGET_SUCCESSES=${TARGET_SUCCESSES:-5}
MAX_ATTEMPTS=${MAX_ATTEMPTS:-20}
CSV_FILE=${CSV_FILE:-first_touch_results.csv}
LOG_DIR=${LOG_DIR:-${CSV_FILE%.csv}.logs}
CPU=${CPU:-2}

for value in "$NUM_RUNS" "$TARGET_SUCCESSES" "$MAX_ATTEMPTS"; do
  [[ "$value" =~ ^[1-9][0-9]*$ ]] || { echo "sample/attempt counts must be positive integers" >&2; exit 1; }
done
[[ "$CPU" =~ ^[0-9]+$ && "$THRESHOLD_PCT" =~ ^[0-9]+([.][0-9]+)?$ ]] || {
  echo "invalid CPU or retention threshold" >&2; exit 1;
}
awk "BEGIN {exit !($THRESHOLD_PCT <= 100)}" || { echo "retention threshold exceeds 100%" >&2; exit 1; }
[[ ! -e "$CSV_FILE" && ! -e "$LOG_DIR" ]] || {
  echo "CSV_FILE and LOG_DIR must be new paths; existing evidence is preserved" >&2; exit 1;
}

if [ ! -x ./benchmark_first_touch ]; then
  echo "benchmark_first_touch is missing; run make first." >&2
  exit 1
fi

taskset -c "$CPU" true
mkdir "$LOG_DIR"
cp ./benchmark_first_touch "$LOG_DIR/benchmark_first_touch"
{
  printf 'protocol=first-touch-raw-v1\nstarted_at='; date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'kernel='; uname -r
  printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
  printf 'cpu=%s\nruns_per_attempt=%s\nthreshold_pct=%s\ntarget_successes=%s\nmax_attempts=%s\n' \
    "$CPU" "$NUM_RUNS" "$THRESHOLD_PCT" "$TARGET_SUCCESSES" "$MAX_ATTEMPTS"
  printf 'targets=%s\nconditions=%s\nstub_dso=%s\nnative_dso=%s\n' \
    "${TARGETS[*]}" "${CONDITIONS[*]}" "$STUB_DSO" "$NATIVE_DSO"
  printf 'input_bytes=5\nseed=0x1234\n'
  taskset -c "$CPU" sh -c 'awk "/^Cpus_allowed_list:/ {print}" /proc/self/status'
} > "$LOG_DIR/environment.txt"
ATTEMPTS_CSV="$LOG_DIR/attempts.csv"
echo "target,condition,attempt,exit_status,total_runs,expected_fault_runs,iqr_retained,fault_mismatches,retained_pct,decision,reason" > "$ATTEMPTS_CSV"
incomplete=0

echo "Target,Condition,Valid_Batches,Grand_Median,Grand_Mean,Avg_StdDev,Avg_P25,Avg_P75,Avg_P95,Avg_Minor_Flt,Avg_Major_Flt" > "$CSV_FILE"

echo "=========================================================="
echo " first-touch benchmark: native/stub x ${CONDITIONS[*]}"
echo " runs per batch: $NUM_RUNS"
echo " valid batch threshold: $THRESHOLD_PCT% retained after IQR filtering"
echo " target valid batches: $TARGET_SUCCESSES, max attempts: $MAX_ATTEMPTS"
echo " output: $CSV_FILE"
echo " stub dso: $STUB_DSO"
echo " native dso: $NATIVE_DSO"
echo "=========================================================="

extract_value() {
  local label=$1
  awk -F': ' -v label="$label" '!found && $1 == label {print $2; found=1}'
}

for target in "${TARGETS[@]}"; do
  for condition in "${CONDITIONS[@]}"; do
    echo
    echo "--> $target / $condition"

    valid_count=0
    sum_median=0
    sum_mean=0
    sum_stddev=0
    sum_p25=0
    sum_p75=0
    sum_p95=0
    sum_minor=0
    sum_major=0
    group_dir="$LOG_DIR/$target/$condition"
    mkdir -p "$group_dir"

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
      printf "  attempt %d/%d [valid %d/%d] ... " \
        "$attempt" "$MAX_ATTEMPTS" "$valid_count" "$TARGET_SUCCESSES"

      prefix="$group_dir/attempt-$(printf '%02d' "$attempt")"
      if taskset -c "$CPU" "$LOG_DIR/benchmark_first_touch" -t "$target" -s "$condition" \
        -n "$NUM_RUNS" -o "$prefix.samples.csv" > "$prefix.stdout" 2> "$prefix.stderr"; then
        status=0
      else
        status=$?
      fi
      if [ "$status" -ne 0 ]; then
        echo "$target,$condition,$attempt,$status,,,,,,failed,benchmark_error" >> "$ATTEMPTS_CSV"
        echo "failed (exit $status); records retained at $prefix" >&2
        exit "$status"
      fi
      output=$(cat "$prefix.stdout")
      total=$(printf '%s\n' "$output" | extract_value "Total Runs")
      expected=$(printf '%s\n' "$output" | extract_value "Expected-Fault Runs" | awk '{print $1}')
      filtered=$(printf '%s\n' "$output" | extract_value "Valid Runs (IQR)" | awk '{print $1}')
      mismatches=$(printf '%s\n' "$output" | extract_value "Fault Mismatches")
      retained=$(printf '%s\n' "$output" | extract_value "Valid Runs (IQR)" | awk '{gsub(/[()%]/, "", $2); print $2}')

      if [[ -z "$retained" || ! "$total" =~ ^[0-9]+$ || ! "$expected" =~ ^[0-9]+$ || \
            ! "$filtered" =~ ^[0-9]+$ || ! "$mismatches" =~ ^[0-9]+$ ]]; then
        echo "$target,$condition,$attempt,$status,$total,$expected,$filtered,$mismatches,$retained,failed,parse_error" >> "$ATTEMPTS_CSV"
        echo "parse failed"
        exit 1
      fi

      is_valid=$(awk "BEGIN {print ($retained >= $THRESHOLD_PCT) ? 1 : 0}")
      if [ "$is_valid" -ne 1 ]; then
        echo "$target,$condition,$attempt,$status,$total,$expected,$filtered,$mismatches,$retained,rejected,retention_below_threshold" >> "$ATTEMPTS_CSV"
        echo "rejected (${retained}% retained)"
        continue
      fi
      echo "$target,$condition,$attempt,$status,$total,$expected,$filtered,$mismatches,$retained,accepted,retention_threshold_met" >> "$ATTEMPTS_CSV"

      median=$(printf '%s\n' "$output" | extract_value "Median Cycles")
      mean=$(printf '%s\n' "$output" | extract_value "Mean Cycles")
      stddev=$(printf '%s\n' "$output" | extract_value "Std Deviation")
      p25=$(printf '%s\n' "$output" | extract_value "P25 Cycles")
      p75=$(printf '%s\n' "$output" | extract_value "P75 Cycles")
      p95=$(printf '%s\n' "$output" | extract_value "P95 Cycles")
      minor=$(printf '%s\n' "$output" | extract_value "Avg Minor Faults" | awk '{print $1}')
      major=$(printf '%s\n' "$output" | extract_value "Avg Major Faults" | awk '{print $1}')

      sum_median=$(awk "BEGIN {print $sum_median + $median}")
      sum_mean=$(awk "BEGIN {print $sum_mean + $mean}")
      sum_stddev=$(awk "BEGIN {print $sum_stddev + $stddev}")
      sum_p25=$(awk "BEGIN {print $sum_p25 + $p25}")
      sum_p75=$(awk "BEGIN {print $sum_p75 + $p75}")
      sum_p95=$(awk "BEGIN {print $sum_p95 + $p95}")
      sum_minor=$(awk "BEGIN {print $sum_minor + $minor}")
      sum_major=$(awk "BEGIN {print $sum_major + $major}")

      valid_count=$((valid_count + 1))
      echo "accepted (${retained}% retained)"

      if [ "$valid_count" -ge "$TARGET_SUCCESSES" ]; then
        break
      fi

      sleep 0.5
    done

    if [ "$valid_count" -eq 0 ]; then
      incomplete=1
      echo "$target,$condition,0,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "$CSV_FILE"
      echo "  no valid batches"
      continue
    fi
    if [ "$valid_count" -lt "$TARGET_SUCCESSES" ]; then
      incomplete=1
    fi

    grand_median=$(awk "BEGIN {printf \"%.0f\", $sum_median / $valid_count}")
    grand_mean=$(awk "BEGIN {printf \"%.2f\", $sum_mean / $valid_count}")
    avg_stddev=$(awk "BEGIN {printf \"%.2f\", $sum_stddev / $valid_count}")
    avg_p25=$(awk "BEGIN {printf \"%.0f\", $sum_p25 / $valid_count}")
    avg_p75=$(awk "BEGIN {printf \"%.0f\", $sum_p75 / $valid_count}")
    avg_p95=$(awk "BEGIN {printf \"%.0f\", $sum_p95 / $valid_count}")
    avg_minor=$(awk "BEGIN {printf \"%.2f\", $sum_minor / $valid_count}")
    avg_major=$(awk "BEGIN {printf \"%.2f\", $sum_major / $valid_count}")

    echo "$target,$condition,$valid_count,$grand_median,$grand_mean,$avg_stddev,$avg_p25,$avg_p75,$avg_p95,$avg_minor,$avg_major" >> "$CSV_FILE"
    echo "  aggregate median: $grand_median cycles from $valid_count valid batches"
  done
done

echo "=========================================================="
echo "done: $CSV_FILE"
echo "=========================================================="
if [ "$incomplete" -ne 0 ]; then
  echo "incomplete: one or more groups did not reach the accepted-batch target" >&2
  exit 2
fi
printf 'status=complete\n' > "$LOG_DIR/complete.txt"
