#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${REPO_ROOT}/backups"
STAMP="${1:-pre_optuna_$(date +%Y%m%d_%H%M%S)}"
ARCHIVE_PATH="${BACKUP_ROOT}/${STAMP}.tar"
SHA_PATH="${ARCHIVE_PATH}.sha256"

INCLUDES=(
  "data"
  "results"
  "scripts"
  "logs"
  "tensorboard"
  "manuscript/data"
  "configs/optuna_datasets.json"
  "README.md"
)

mkdir -p "${BACKUP_ROOT}"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

MANIFEST_PATH="${TMP_DIR}/backup_manifest.txt"
GIT_REV_PATH="${TMP_DIR}/git_rev.txt"
GIT_STATUS_PATH="${TMP_DIR}/git_status.txt"

{
  echo "backup_name=${STAMP}"
  echo "created_at=$(date --iso-8601=seconds)"
  echo "repo_root=${REPO_ROOT}"
  echo "archive_path=${ARCHIVE_PATH}"
  echo "included_paths="
  for item in "${INCLUDES[@]}"; do
    echo "  - ${item}"
  done
} > "${MANIFEST_PATH}"

git -C "${REPO_ROOT}" rev-parse HEAD > "${GIT_REV_PATH}" || true
git -C "${REPO_ROOT}" status --short > "${GIT_STATUS_PATH}" || true

tar -cf "${ARCHIVE_PATH}" \
  -C "${REPO_ROOT}" "${INCLUDES[@]}" \
  -C "${TMP_DIR}" "$(basename "${MANIFEST_PATH}")" "$(basename "${GIT_REV_PATH}")" "$(basename "${GIT_STATUS_PATH}")"

sha256sum "${ARCHIVE_PATH}" > "${SHA_PATH}"

echo "Created backup archive:"
echo "  ${ARCHIVE_PATH}"
echo "Checksum:"
echo "  ${SHA_PATH}"
