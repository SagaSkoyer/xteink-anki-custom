#!/usr/bin/env bash
set -euo pipefail

# Clones the pinned CrossPoint checkout that owns the SD-card font converter
# (lib/EpdFont/scripts/fontconvert_sdcard.py). Same version pin as
# custom-bin-builds/patches, kept independently so this folder still works if
# that pin ever moves — the converter itself is version-agnostic.

readonly CROSSPOINT_VERSION="1.6.0rc"
readonly CROSSPOINT_COMMIT="6a501bba544d9e80598811dbdf2134d1bcb1ebd2"
readonly CROSSPOINT_REPOSITORY="https://github.com/crosspoint-reader/crosspoint-reader.git"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
source_dir="${repo_dir}/.firmware-build/crosspoint-reader-${CROSSPOINT_VERSION}"

if [[ ! -d "${source_dir}/.git" ]]; then
  mkdir -p "$(dirname "${source_dir}")"
  git clone \
    --branch "${CROSSPOINT_VERSION}" \
    --depth 1 \
    "${CROSSPOINT_REPOSITORY}" \
    "${source_dir}"
fi

actual_commit="$(git -C "${source_dir}" rev-parse HEAD)"
if [[ "${actual_commit}" != "${CROSSPOINT_COMMIT}" ]]; then
  printf 'Expected CrossPoint %s at %s, found %s\n' \
    "${CROSSPOINT_VERSION}" "${CROSSPOINT_COMMIT}" "${actual_commit}" >&2
  exit 1
fi

printf '%s\n' "${source_dir}"
