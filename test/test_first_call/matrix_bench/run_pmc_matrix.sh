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

PMC_RUNS=${PMC_RUNS:-30}
PMC_CSV=${PMC_CSV:-pmc_results.csv}
PMC_LOG_DIR=${PMC_LOG_DIR:-pmc_logs}
TASKSET_CPU=${TASKSET_CPU:-1}

if [ ! -x ./benchmark_pmc ]; then
  echo "benchmark_pmc is missing; run make first." >&2
  exit 1
fi

mkdir -p "$PMC_LOG_DIR"

echo "Target,Condition,Total_Runs,Expected_Fault_Runs,Valid_Runs,Fault_Mismatches,Avg_Minor_Flt,Avg_Major_Flt,Median_TSC_Cycles,Mean_TSC_Cycles,StdDev_TSC,Mean_Perf_Cycles,Mean_Instructions,Mean_L1I_Misses,Mean_L1D_Misses,Mean_LLC_Misses,Mean_iTLB_Misses" > "$PMC_CSV"

echo "=========================================================="
echo " PMU benchmark: native/stub x ${CONDITIONS[*]}"
echo " runs per group: $PMC_RUNS"
echo " output: $PMC_CSV"
echo " logs: $PMC_LOG_DIR"
echo " cpu: $TASKSET_CPU"
echo " stub dso: $STUB_DSO"
echo " native dso: $NATIVE_DSO"
echo "=========================================================="

extract_value() {
  local label=$1
  awk -F': ' -v label="$label" '$1 == label {print $2; exit}'
}

extract_first_number() {
  awk '{print $1}'
}

for target in "${TARGETS[@]}"; do
  for condition in "${CONDITIONS[@]}"; do
    echo
    echo "--> $target / $condition"

    log_file="$PMC_LOG_DIR/pmc_${target}_${condition}.txt"
    taskset -c "$TASKSET_CPU" ./benchmark_pmc -t "$target" -s "$condition" -n "$PMC_RUNS" | tee "$log_file"

    total_runs=$(extract_value "Total Runs" < "$log_file")
    expected_runs=$(extract_value "Expected-Fault Runs" < "$log_file" | extract_first_number)
    valid_runs=$(extract_value "Valid Runs (IQR)" < "$log_file" | extract_first_number)
    fault_mismatches=$(extract_value "Fault Mismatches" < "$log_file")
    avg_minor=$(extract_value "Avg Minor Faults" < "$log_file" | extract_first_number)
    avg_major=$(extract_value "Avg Major Faults" < "$log_file" | extract_first_number)
    median_tsc=$(extract_value "Median TSC Cycles" < "$log_file")
    mean_tsc=$(extract_value "Mean TSC Cycles" < "$log_file")
    stddev_tsc=$(extract_value "Std Deviation" < "$log_file")
    perf_cycles=$(extract_value "Mean Perf Cycles" < "$log_file")
    instructions=$(extract_value "Mean Instructions" < "$log_file")
    l1i=$(extract_value "Mean L1I Misses" < "$log_file")
    l1d=$(extract_value "Mean L1D Misses" < "$log_file")
    llc=$(extract_value "Mean LLC Misses" < "$log_file")
    itlb=$(extract_value "Mean iTLB Misses" < "$log_file")

    echo "$target,$condition,$total_runs,$expected_runs,$valid_runs,$fault_mismatches,$avg_minor,$avg_major,$median_tsc,$mean_tsc,$stddev_tsc,$perf_cycles,$instructions,$l1i,$l1d,$llc,$itlb" >> "$PMC_CSV"
  done
done

echo "=========================================================="
echo "done: $PMC_CSV"
echo "=========================================================="
