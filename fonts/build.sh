#!/usr/bin/env bash
set -euo pipefail

# Convert a TTF/OTF family in fonts/input/ into the .cpfont set CrossPoint
# loads from the SD card, using the firmware's own converter
# (lib/EpdFont/scripts/fontconvert_sdcard.py) so the output matches what the
# web builder at https://crosspointreader.com/fonts produces.
#
# Usage:
#   ./fonts/build.sh <FamilyName> [--intervals LIST] [--sizes LIST]
#
# Looks for fonts/input/<FamilyName>-{Regular,Bold,Italic,BoldItalic}.{ttf,otf}
# and converts whichever of the four styles exist. Output goes to
# fonts/output/<FamilyName>/.
#
# Default coverage (--intervals latin-ext,greek,cyrillic,cjk) matches the
# "default" and "Chinese-simplified" combination CrossPoint expects of one SD
# family (docs/sd-card-fonts.md, "CJK in the User Interface"):
#   - latin-ext,greek,cyrillic is the same coverage as the pre-built catalog
#     families (see any entry's "scripts" in the crosspoint-fonts manifest),
#     so the family stands alone as a full reader/UI font ("default") rather
#     than needing a fallback of its own.
#   - cjk adds the ~22,000 CJK Unified Ideographs + Hiragana/Katakana/
#     Fullwidth codepoints. A CJK-capable family selected under Settings >
#     Reader > Font Family is what CrossPoint uses as the size-matched
#     fallback for CJK text in the UI (book titles, file names, list rows) —
#     see docs/sd-card-fonts.md. Selecting a family that lacks Latin/Greek/
#     Cyrillic coverage of its own would leave *non*-CJK UI text falling back
#     to a font with no matching glyphs for it.
#
# Default sizes (8,10,12,14,16,18) matter for the same reason as the built-in
# UI fonts: 8/10/12 back the interface (small/list-row/header text) and the
# CJK UI fallback (kUiFontSizes in src/SdCardFontSystem.cpp), 12-18 back the
# reader, and 18 specifically backs Anki's Medium card size (UI_18_FONT_ID).
# Omitting any of the six leaves that size showing boxes for CJK text.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
input_dir="${script_dir}/input"
output_root="${script_dir}/output"

intervals="latin-ext,greek,cyrillic,cjk"
sizes="8,10,12,14,16,18"

if [[ $# -lt 1 ]]; then
  printf 'Usage: %s <FamilyName> [--intervals LIST] [--sizes LIST]\n' "$0" >&2
  exit 1
fi
family="$1"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --intervals) intervals="$2"; shift 2 ;;
    --sizes) sizes="$2"; shift 2 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 1 ;;
  esac
done

source_dir="$("${script_dir}/prepare.sh" | tail -n 1)"
converter="${source_dir}/lib/EpdFont/scripts/fontconvert_sdcard.py"

python3 -m pip show freetype-py fonttools >/dev/null 2>&1 || \
  python3 -m pip install --quiet -r "${source_dir}/lib/EpdFont/scripts/requirements.txt"

style_args=()
found_any=0
for style_name in Regular Bold Italic BoldItalic; do
  flag="--$(printf '%s' "${style_name}" | tr '[:upper:]' '[:lower:]')"
  for ext in ttf otf; do
    candidate="${input_dir}/${family}-${style_name}.${ext}"
    if [[ -f "${candidate}" ]]; then
      style_args+=("${flag}" "${candidate}")
      found_any=1
      break
    fi
  done
done

if [[ "${found_any}" -eq 0 ]]; then
  printf 'No %s/%s-{Regular,Bold,Italic,BoldItalic}.{ttf,otf} files found\n' "${input_dir}" "${family}" >&2
  exit 1
fi

output_dir="${output_root}/${family}"
rm -rf "${output_dir}"
mkdir -p "${output_dir}"

python3 "${converter}" \
  "${style_args[@]}" \
  --intervals "${intervals}" \
  --sizes "${sizes}" \
  --name "${family}" \
  --output-dir "${output_dir}"

printf 'Wrote %s:\n' "${output_dir}"
ls -la "${output_dir}"
