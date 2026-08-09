#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
if [[ $# -gt 0 ]]; then
  source_dir="$("${script_dir}/prepare.sh" "$1" | tail -n 1)"
else
  source_dir="$("${script_dir}/prepare.sh" | tail -n 1)"
fi
output_file="${repo_dir}/dist/crosspoint-1.4.1-xteink-anki.bin"

# Resolve PlatformIO even when not on PATH (common: ~/.platformio/penv).
platformio_command=()
if command -v pio >/dev/null 2>&1; then
  platformio_command=(pio)
elif command -v platformio >/dev/null 2>&1; then
  platformio_command=(platformio)
elif [[ -x "${HOME}/.platformio/penv/bin/pio" ]]; then
  platformio_command=("${HOME}/.platformio/penv/bin/pio")
elif [[ -x "${HOME}/.platformio/penv/bin/platformio" ]]; then
  platformio_command=("${HOME}/.platformio/penv/bin/platformio")
else
  printf 'PlatformIO/pioarduino was not found in PATH or ~/.platformio/penv/bin.\n' >&2
  exit 1
fi

"${platformio_command[@]}" run --project-dir "${source_dir}" -e gh_release

# UI_12 (small/large) and UI_18 (native medium) must both carry DE/Greek/romanization.
for font_header in \
  "${source_dir}/lib/EpdFont/builtinFonts/ubuntu_12_regular.h" \
  "${source_dir}/lib/EpdFont/builtinFonts/ubuntu_18_regular.h"
do
  for required_glyph in U+00DF U+00E4 U+037E U+0387 U+03B1 U+03C9 U+1F00 U+1E53; do
    if ! grep -Fq "${required_glyph}" "${font_header}"; then
      printf 'Required Anki font glyph %s is missing from %s\n' \
        "${required_glyph}" "${font_header}" >&2
      exit 1
    fi
  done
done

install -m 0644 "${source_dir}/.pio/build/gh_release/firmware.bin" "${output_file}"

printf 'Firmware: %s\n' "${output_file}"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${output_file}"
fi
