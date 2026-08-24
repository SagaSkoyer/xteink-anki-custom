#!/usr/bin/env bash
set -euo pipefail

# Package the Anki Desktop add-on from ../xteink_sync into an installable
# .ankiaddon (a plain zip with the add-on files at the archive root).

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
source_dir="${repo_dir}/xteink_sync"
output_file="${script_dir}/xteink_sync.ankiaddon"

python3 -m py_compile "${source_dir}"/*.py
python3 -m unittest discover -s "${repo_dir}/tests"

rm -f "${output_file}"
(
  cd "${source_dir}"
  zip -q -r -X "${output_file}" \
    __init__.py config.json config.md manifest.json \
    mdns_advertise.py protocol.py textutil.py user_files \
    -x '*/__pycache__/*' '*.pyc'
)

printf 'Add-on: %s\n' "${output_file}"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${output_file}"
else
  sha256sum "${output_file}"
fi
