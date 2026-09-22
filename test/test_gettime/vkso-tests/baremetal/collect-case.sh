#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Internal implementation of experiment.sh collect; never launch a second protocol.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CASE=${1:?case required}
: "${DIRECT_PACKAGE:?run ./experiment.sh collect}"
: "${DIRECT_OUT:?run ./experiment.sh collect}"
: "${DIRECT_CONFIG:?run ./experiment.sh collect}"
if [[ $(id -u) -ne 0 ]]; then
    exec sudo --preserve-env=DIRECT_PACKAGE,DIRECT_OUT,DIRECT_CONFIG,DIRECT_BLOCK "$0" "$@"
fi
# Tuning is performed only after basic target identity checks. Full preflight below
# additionally verifies installed image, auxv, controls and all checksummed artifacts.
test "$(uname -r)" = 5.15.198 || { echo 'wrong kernel: requires experimental 5.15.198' >&2; exit 1; }
backend=${CASE%%-*}
case "$CASE" in raw-normal|vkso-normal|raw-no-retpoline|vkso-no-retpoline) ;; *) exit 2 ;; esac
cmp -s <(zcat /proc/config.gz) "$DIRECT_PACKAGE/$backend.config" || {
    echo 'wrong kernel config' >&2; exit 1;
}
python3 - "$DIRECT_PACKAGE" "$backend" <<'PY'
import platform,sys
from pathlib import Path
m=dict(line.split('=',1) for line in (Path(sys.argv[1])/'boot-manifest.txt').read_text().splitlines() if '=' in line)
if platform.version()!=m[sys.argv[2]+'_uts_version']: sys.exit('wrong kernel build identity')
PY
saved_paths=() saved_values=()
irq_active=0
restore() {
    status=$?
    trap - EXIT
    set +e
    for ((i=${#saved_paths[@]}-1; i>=0; --i)); do
        printf '%s\n' "${saved_values[$i]}" >"${saved_paths[$i]}" || status=1
    done
    if [[ $irq_active == 1 ]]; then systemctl start irqbalance || status=1; fi
    if [[ -n ${SUDO_UID:-} && -d "$DIRECT_OUT" ]]; then
        chown -R "$SUDO_UID:$SUDO_GID" "$DIRECT_OUT" || status=1
    fi
    if [[ "$status" != 0 && -f "$DIRECT_OUT/run.json" ]]; then
        python3 - "$DIRECT_OUT" <<'RECORD'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);p=out/'run.json'
r=json.loads(p.read_text());r['status']='FAIL';r['environment_cleanup_status']='FAIL'
p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n'
    for f in sorted(out.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))
RECORD
    fi
    exit "$status"
}
trap restore EXIT
set_value() {
    test -r "$1"
    saved_paths+=("$1"); saved_values+=("$(cat "$1")")
    printf '%s\n' "$2" >"$1"
}
set_value /sys/devices/system/cpu/intel_pstate/no_turbo 1
set_value /sys/devices/system/cpu/intel_pstate/max_perf_pct 100
set_value /sys/devices/system/cpu/intel_pstate/min_perf_pct 100
for path in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do set_value "$path" performance; done
if systemctl is-active --quiet irqbalance; then
    irq_active=1
    systemctl stop irqbalance
fi
mapfile -t values < <(python3 - <<'PY'
import json,os
c=json.loads(os.environ['DIRECT_CONFIG'])
for key in ('CPU','ITERATIONS','WARMUP','REPEATS','PERF_PROCESSES'): print(int(c[key]))
PY
)
echo "collecting=$CASE output=$DIRECT_OUT (validation, then public READ)"
python3 "$HERE/../direct-api/collect.py" --execute --case "$CASE" \
    --bundle "$DIRECT_PACKAGE/direct" --out "$DIRECT_OUT" \
    --cpu "${values[0]}" --iterations "${values[1]}" --warmup "${values[2]}" \
    --repeats "${values[3]}" --processes "${values[4]}"
