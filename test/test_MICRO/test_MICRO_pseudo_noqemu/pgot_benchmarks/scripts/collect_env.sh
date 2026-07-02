#!/usr/bin/env bash
set -euo pipefail

emit() {
  local key="$1"
  local value="${2:-unknown}"
  value="${value//$'\n'/ }"
  value="${value//$'\r'/ }"
  echo "# ${key}=${value}"
}

read_one_line() {
  local path="$1"
  if [[ -r "${path}" ]]; then
    tr '\n' ' ' < "${path}" | sed 's/[[:space:]]*$//'
  else
    printf 'unavailable'
  fi
}

emit_cmd() {
  local key="$1"
  shift
  local value
  if value="$("$@" 2>/dev/null)"; then
    emit "${key}" "${value}"
  else
    emit "${key}" "unavailable"
  fi
}

cpu_for_cpufreq="${CPU:-0}"
cpufreq_dir="/sys/devices/system/cpu/cpu${cpu_for_cpufreq}/cpufreq"

emit_cmd "date_utc" date -u "+%Y-%m-%dT%H:%M:%SZ"
emit "uname" "$(uname -a)"
emit "kernel_cmdline" "$(read_one_line /proc/cmdline)"
emit "online_cpus" "$(read_one_line /sys/devices/system/cpu/online)"
emit "isolated_cpus" "$(read_one_line /sys/devices/system/cpu/isolated)"
emit "nohz_full_cpus" "$(read_one_line /sys/devices/system/cpu/nohz_full)"
emit "rcu_nocbs_cpus" "$(read_one_line /sys/devices/system/cpu/rcu_nocbs)"
emit "requested_cpu" "${CPU:-unpinned}"

if [[ -r "${cpufreq_dir}/scaling_governor" ]]; then
  emit "cpu${cpu_for_cpufreq}_governor" "$(read_one_line "${cpufreq_dir}/scaling_governor")"
else
  governors="$(find /sys/devices/system/cpu -path '*/cpufreq/scaling_governor' -type f -readable -print 2>/dev/null | sort | xargs -r cat 2>/dev/null | sort -u | paste -sd ' ' -)"
  emit "governors" "${governors:-unavailable}"
fi

if [[ -r /sys/devices/system/cpu/intel_pstate/no_turbo ]]; then
  no_turbo="$(read_one_line /sys/devices/system/cpu/intel_pstate/no_turbo)"
  if [[ "${no_turbo}" == "0" ]]; then
    emit "intel_turbo" "enabled"
  elif [[ "${no_turbo}" == "1" ]]; then
    emit "intel_turbo" "disabled"
  else
    emit "intel_turbo" "unknown:${no_turbo}"
  fi
elif [[ -r /sys/devices/system/cpu/cpufreq/boost ]]; then
  boost="$(read_one_line /sys/devices/system/cpu/cpufreq/boost)"
  if [[ "${boost}" == "1" ]]; then
    emit "cpu_boost" "enabled"
  elif [[ "${boost}" == "0" ]]; then
    emit "cpu_boost" "disabled"
  else
    emit "cpu_boost" "unknown:${boost}"
  fi
else
  emit "turbo_or_boost" "unavailable"
fi

emit "smt_active" "$(read_one_line /sys/devices/system/cpu/smt/active)"
emit "spectre_v2_mitigation" "$(read_one_line /sys/devices/system/cpu/vulnerabilities/spectre_v2)"

if command -v lscpu >/dev/null 2>&1; then
  emit "cpu_model" "$(lscpu | awk -F: '/Model name:/ { sub(/^[ \t]+/, "", $2); print $2; exit }')"
  emit "cpu_topology" "$(lscpu | awk -F: '$1 == "CPU(s)" || $1 == "Thread(s) per core" || $1 == "Core(s) per socket" || $1 == "Socket(s)" { gsub(/^[ \t]+/, "", $2); printf "%s=%s; ", $1, $2 }')"
fi

compiler_version="$("${CC:-cc}" --version 2>/dev/null | sed -n '1p' || true)"
emit "compiler" "${compiler_version:-unavailable}"
emit_cmd "compiler_target" "${CC:-cc}" -dumpmachine
