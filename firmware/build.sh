#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
source_dir="$("${script_dir}/prepare.sh" "${1:-${repo_dir}/.firmware-build/crosspoint-reader-1.4.1}" | tail -n 1)"
output_file="${repo_dir}/dist/crosspoint-1.4.1-xteink-anki.bin"

if command -v pio >/dev/null 2>&1; then
  platformio_command=(pio)
elif command -v platformio >/dev/null 2>&1; then
  platformio_command=(platformio)
else
  printf 'PlatformIO/pioarduino was not found in PATH.\n' >&2
  exit 1
fi

"${platformio_command[@]}" run --project-dir "${source_dir}" -e gh_release
install -m 0644 "${source_dir}/.pio/build/gh_release/firmware.bin" "${output_file}"

printf 'Firmware: %s\n' "${output_file}"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${output_file}"
fi
