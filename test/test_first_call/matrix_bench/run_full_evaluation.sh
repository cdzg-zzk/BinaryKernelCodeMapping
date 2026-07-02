#!/usr/bin/env bash
set -euo pipefail

export STUB_DSO=${STUB_DSO:-$(realpath ../tmp/libzzk_xxh32_lkm.so)}
export NATIVE_DSO=${NATIVE_DSO:-$(realpath ../so/libclone_xxh32.so)}

LATENCY_CSV=${LATENCY_CSV:-first_touch_results.csv}
PMC_CSV=${PMC_CSV:-pmc_results.csv}
COMBINED_CSV=${COMBINED_CSV:-first_touch_pmu_combined.csv}

for bin in ./benchmark_first_touch ./benchmark_pmc ./benchmark_ftrace; do
  if [ ! -x "$bin" ]; then
    echo "$bin is missing; run make first." >&2
    exit 1
  fi
done

CSV_FILE="$LATENCY_CSV" ./run_benchmarks.sh
PMC_CSV="$PMC_CSV" ./run_pmc_matrix.sh
./merge_latency_pmu.py --latency "$LATENCY_CSV" --pmu "$PMC_CSV" -o "$COMBINED_CSV"

echo "=========================================================="
echo "combined table: $COMBINED_CSV"
echo
echo "Run ftrace minor-fault comparison separately:"
echo "  sudo STUB_DSO=$STUB_DSO NATIVE_DSO=$NATIVE_DSO ./benchmark_ftrace -t native -s pte-cold -o ftrace_native_ptecold.log"
echo "  sudo STUB_DSO=$STUB_DSO NATIVE_DSO=$NATIVE_DSO ./benchmark_ftrace -t stub -s pte-cold -o ftrace_stub_ptecold.log"
echo "=========================================================="
