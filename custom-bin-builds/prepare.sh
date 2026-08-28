#!/usr/bin/env bash
set -euo pipefail

# Clone the pinned CrossPoint 1.6.0 beta RC and apply the Anki patch.
# Prints the prepared source directory on the last line.

readonly CROSSPOINT_VERSION="1.6.0rc"
readonly CROSSPOINT_COMMIT="6a501bba544d9e80598811dbdf2134d1bcb1ebd2"
readonly CROSSPOINT_REPOSITORY="https://github.com/crosspoint-reader/crosspoint-reader.git"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
patch_file="${script_dir}/patches/crosspoint-${CROSSPOINT_VERSION}-anki.patch"

# One checkout, reused for every build. Editing the patch resets this tree back
# to the pinned commit and re-applies it; the PlatformIO caches (.pio, .cache)
# survive, so a patch edit costs an incremental rebuild rather than a fresh
# 1.3 GB clone plus a cold ~15 minute build.
managed_checkout=1
if [[ $# -gt 0 ]]; then
  # Caller-supplied tree: apply onto it as-is, never reset it.
  source_dir="$1"
  managed_checkout=0
else
  source_dir="${repo_dir}/.firmware-build/crosspoint-reader-${CROSSPOINT_VERSION}"
fi

if [[ ! -d "${source_dir}/.git" ]]; then
  mkdir -p "$(dirname "${source_dir}")"
  git clone \
    --branch "${CROSSPOINT_VERSION}" \
    --depth 1 \
    --recurse-submodules \
    "${CROSSPOINT_REPOSITORY}" \
    "${source_dir}"
fi

if [[ "${managed_checkout}" == "1" ]]; then
  git -C "${source_dir}" reset --hard --quiet "${CROSSPOINT_COMMIT}"
  # Keep the build caches and any local PlatformIO overrides; drop everything
  # else the previous patch left behind.
  git -C "${source_dir}" clean -fdq \
    -e .pio \
    -e .cache \
    -e platformio.local.ini
fi

actual_commit="$(git -C "${source_dir}" rev-parse HEAD)"
if [[ "${actual_commit}" != "${CROSSPOINT_COMMIT}" ]]; then
  printf 'Expected CrossPoint %s at %s, found %s\n' \
    "${CROSSPOINT_VERSION}" "${CROSSPOINT_COMMIT}" "${actual_commit}" >&2
  exit 1
fi

git -C "${source_dir}" submodule update --init --recursive

if git -C "${source_dir}" apply --reverse --check "${patch_file}" >/dev/null 2>&1; then
  printf 'Anki firmware patch is already applied in %s\n' "${source_dir}"
elif git -C "${source_dir}" apply --check "${patch_file}"; then
  git -C "${source_dir}" apply "${patch_file}"
  printf 'Applied Anki firmware patch in %s\n' "${source_dir}"
else
  printf 'The CrossPoint checkout contains changes that conflict with the Anki patch: %s\n' \
    "${source_dir}" >&2
  exit 1
fi

printf '%s\n' "${source_dir}"
