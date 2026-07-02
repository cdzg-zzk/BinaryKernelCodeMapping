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

if [ ! -x ./benchmark_first_touch ]; then
  echo "benchmark_first_touch is missing; run make first." >&2
  exit 1
fi

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
  awk -F': ' -v label="$label" '$1 == label {print $2; exit}'
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

    for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
      printf "  attempt %d/%d [valid %d/%d] ... " \
        "$attempt" "$MAX_ATTEMPTS" "$valid_count" "$TARGET_SUCCESSES"

      output=$(./benchmark_first_touch -t "$target" -s "$condition" -n "$NUM_RUNS")
      retained=$(printf '%s\n' "$output" | grep -oP '(?<=\()[0-9.]+(?=% retained)' | head -n1 || true)

      if [ -z "$retained" ]; then
        echo "parse failed"
        continue
      fi

      is_valid=$(awk "BEGIN {print ($retained >= $THRESHOLD_PCT) ? 1 : 0}")
      if [ "$is_valid" -ne 1 ]; then
        echo "rejected (${retained}% retained)"
        continue
      fi

      median=$(printf '%s\n' "$output" | extract_value "Median Cycles")
      mean=$(printf '%s\n' "$output" | extract_value "Mean Cycles")
      stddev=$(printf '%s\n' "$output" | extract_value "Std Deviation")
      p25=$(printf '%s\n' "$output" | extract_value "P25 Cycles")
      p75=$(printf '%s\n' "$output" | extract_value "P75 Cycles")
      p95=$(printf '%s\n' "$output" | extract_value "P95 Cycles")
      minor=$(printf '%s\n' "$output" | awk -F': ' '$1 == "Avg Minor Faults" {print $2; exit}' | awk '{print $1}')
      major=$(printf '%s\n' "$output" | awk -F': ' '$1 == "Avg Major Faults" {print $2; exit}' | awk '{print $1}')

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
      echo "$target,$condition,0,N/A,N/A,N/A,N/A,N/A,N/A,N/A,N/A" >> "$CSV_FILE"
      echo "  no valid batches"
      continue
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
