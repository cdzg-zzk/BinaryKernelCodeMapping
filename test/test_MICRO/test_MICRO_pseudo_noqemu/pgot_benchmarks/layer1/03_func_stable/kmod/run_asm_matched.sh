#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PGOT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PGOT_ROOT}/results/layer1/03_func_stable/kmod_diag_asm_matched}"
ITERATIONS="${ITERATIONS:-1000000}"
REPEATS="${REPEATS:-31}"
OUTER_RUNS="${OUTER_RUNS:-5}"
CPU="${CPU:-2}"
MODULE="bench_kmod"
BUILD_DIR="${OUT_DIR}/.build"
KEEP_BUILD="${KEEP_BUILD:-0}"
KCFLAGS="${KCFLAGS:--mindirect-branch=keep -mfunction-return=keep -DBENCH_NOTRACE=1 -DBENCH_ALIGN64=1 -DBENCH_ASM_MATCHED=1 -DBENCH_ASM_ONLY=1}"

sudo_cmd() {
  if [[ "${SUDO_PASSWORD:-}" != "" ]]; then
    printf '%s\n' "${SUDO_PASSWORD}" | sudo -S "$@"
  else
    sudo "$@"
  fi
}

mkdir -p "${OUT_DIR}"
rm -rf "${BUILD_DIR}" "${OUT_DIR}/raw" "${OUT_DIR}/processed" "${OUT_DIR}/kmsg" "${OUT_DIR}/main"
rm -f \
  "${OUT_DIR}/metadata.txt" \
  "${OUT_DIR}/raw.csv" \
  "${OUT_DIR}/processed.csv" \
  "${OUT_DIR}/paper_main.csv" \
  "${OUT_DIR}/objdump.txt" \
  "${OUT_DIR}/objdump_summary.csv" \
  "${OUT_DIR}/.samples_with_outliers.csv"
rm -f "${OUT_DIR}"/.run_*.log
mkdir -p "${BUILD_DIR}"

{
  echo "experiment=layer1_func_stable_asm_matched"
  echo "source_semantics=matched-layout hand-written asm diagnostic"
  echo "build=no_retpoline"
  echo "iterations=${ITERATIONS}"
  echo "repeats=${REPEATS}"
  echo "outer_runs=${OUTER_RUNS}"
  echo "events=1,2,4,8,16"
  echo "target_pattern=stable"
  echo "sample_order=interleave"
  echo "cpu=${CPU}"
  echo "kcflags=${KCFLAGS}"
  echo "asm_direct_event=call target_0; 5-byte nop; mov %rax,%rdi"
  echo "asm_cached_event=7-byte nop; call *%r13; mov %rax,%rdi"
  echo "asm_pgot_event=mov pgot_func_table(%rip),%r11; call *%r11; mov %rax,%rdi"
  echo "asm_event_bytes_matched=13"
  echo "retpoline_validity=no-retpoline only; hand-written indirect call is not compiler-retpolined"
  echo
  bash "${PGOT_ROOT}/collect_env.sh"
} > "${OUT_DIR}/metadata.txt"

RAW="${OUT_DIR}/raw.csv"
echo "experiment,build,run_id,event,repeat,iterations,empty_cycles,direct_cycles,cached_indirect_cycles,pgot_cycles,delta_cached_direct,delta_pgot_cached,delta_pgot_direct" > "${RAW}"

make -C "${SCRIPT_DIR}" clean
make -C "${SCRIPT_DIR}" all KCFLAGS="${KCFLAGS}"
cp "${SCRIPT_DIR}/${MODULE}.ko" "${BUILD_DIR}/bench_kmod_asm_matched.ko"
objdump -drwC --no-show-raw-insn "${SCRIPT_DIR}/${MODULE}.ko" > "${OUT_DIR}/objdump.txt"

python3 - <<'PY' "${OUT_DIR}/objdump.txt" > "${OUT_DIR}/objdump_summary.csv"
import re
import sys

path = sys.argv[1]
out = open(path).read()
funcs = {}
cur = None
for line in out.splitlines():
    m = re.match(r'^([0-9a-f]+) <(body_asm_(empty|direct|cached|pgot)_(1|2|4|8|16))>:', line)
    if m:
        cur = m.group(2)
        funcs[cur] = []
        continue
    if re.match(r'^[0-9a-f]+ <', line):
        cur = None
    if cur:
        m = re.match(r'\s*([0-9a-f]+):\s+(.+)$', line)
        if m:
            funcs[cur].append((int(m.group(1), 16), m.group(2).strip()))

def loop_bounds(name):
    ins = funcs[name]
    for i, (a, text) in enumerate(ins):
        if text.startswith('jne'):
            m = re.search(r'([0-9a-f]+) <', text)
            if m:
                return int(m.group(1), 16), ins[i + 1][0]
    raise RuntimeError(name)

print('kind,event,loop_bytes,cache_lines_64,insns,slot_loads,call_direct,call_indirect,loop_start_mod64')
for event in [1, 2, 4, 8, 16]:
    for kind in ['empty', 'direct', 'cached', 'pgot']:
        name = f'body_asm_{kind}_{event}'
        ls, le = loop_bounds(name)
        loop = [(a, text) for a, text in funcs[name] if ls <= a < le]
        slot = sum(1 for _, text in loop if 'pgot_func_table' in text)
        cdir = sum(1 for _, text in loop if text.startswith('call') and '*' not in text)
        cind = sum(1 for _, text in loop if text.startswith('call') and '*' in text)
        lines = len(set(a // 64 for a, _ in loop))
        print(f'{kind},{event},{le-ls},{lines},{len(loop)},{slot},{cdir},{cind},{ls % 64}')
PY

for ((run_id = 0; run_id < OUTER_RUNS; run_id++)); do
  echo "==> kmod layer1 func stable asm matched no_retpoline run ${run_id}" >&2
  sudo_cmd dmesg -C
  args=("build=no_retpoline" "iterations=${ITERATIONS}" "repeats=${REPEATS}" "run_id=${run_id}" "cpu=${CPU}")
  sudo_cmd insmod "${SCRIPT_DIR}/${MODULE}.ko" "${args[@]}"
  sudo_cmd rmmod "${MODULE}"
  run_log="${OUT_DIR}/.run_${run_id}.log"
  sudo_cmd dmesg > "${run_log}"
  awk -F'PGOT_L1FS_ASM_RAW,' '/PGOT_L1FS_ASM_RAW,/ {print $2}' "${run_log}" >> "${RAW}"
  rm -f "${run_log}"
done

python3 "${PGOT_ROOT}/scripts/process_layer1_func_stable_asm.py" \
  --raw "${RAW}" \
  --processed "${OUT_DIR}/.samples_with_outliers.csv" \
  --summary "${OUT_DIR}/processed.csv" \
  --paper-main "${OUT_DIR}/paper_main.csv"

rm -f "${OUT_DIR}/.samples_with_outliers.csv"
make -C "${SCRIPT_DIR}" clean
if [[ "${KEEP_BUILD}" != "1" ]]; then
  rm -rf "${BUILD_DIR}"
fi

echo "wrote ${OUT_DIR}" >&2
