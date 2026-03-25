#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${BASE_DIR}/workspace/output"
LOGS_DIR="${BASE_DIR}/workspace/logs"

mkdir -p "${OUTPUT_DIR}" "${LOGS_DIR}"

LOG_FILE="${LOGS_DIR}/export_github.log"

log() {
  local msg="$1"
  echo "${msg}" | tee -a "${LOG_FILE}"
}

fail() {
  local msg="$1"
  log "ERROR | ${msg}"
  echo "${msg}" >&2
  exit 1
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") <output.xml>

Required environment variables:
  GITHUB_EXPORT_REPO_PATH   Absolute path to the local git repository
Optional environment variables:
  GITHUB_EXPORT_BRANCH      Target branch (default: current branch)
  GITHUB_EXPORT_TARGET_DIR  Target directory inside repo (default: .)
  GITHUB_EXPORT_COMMIT_MSG  Commit message (default: auto-generated)
  GITHUB_EXPORT_PUSH        true|false (default: true)

Example:
  export GITHUB_EXPORT_REPO_PATH="/Users/you/projects/my-repo"
  export GITHUB_EXPORT_BRANCH="main"
  export GITHUB_EXPORT_TARGET_DIR="translated-books"
  $(basename "$0") "${OUTPUT_DIR}/my_book.translated.en.xml"
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage
  fail "Missing required argument: <output.xml>"
fi

require_cmd git
require_cmd cp
require_cmd mkdir

SOURCE_XML="$1"

if [[ ! -f "${SOURCE_XML}" ]]; then
  fail "Source file does not exist: ${SOURCE_XML}"
fi

if [[ "${SOURCE_XML##*.}" != "xml" ]]; then
  fail "Source file must be a .xml: ${SOURCE_XML}"
fi

: "${GITHUB_EXPORT_REPO_PATH:=}"
: "${GITHUB_EXPORT_BRANCH:=}"
: "${GITHUB_EXPORT_TARGET_DIR:=.}"
: "${GITHUB_EXPORT_COMMIT_MSG:=}"
: "${GITHUB_EXPORT_PUSH:=true}"

[[ -n "${GITHUB_EXPORT_REPO_PATH}" ]] || fail "GITHUB_EXPORT_REPO_PATH is not set"

if [[ ! -d "${GITHUB_EXPORT_REPO_PATH}" ]]; then
  fail "Repository path does not exist: ${GITHUB_EXPORT_REPO_PATH}"
fi

if [[ ! -d "${GITHUB_EXPORT_REPO_PATH}/.git" ]]; then
  fail "Repository path is not a git repository: ${GITHUB_EXPORT_REPO_PATH}"
fi

REPO_PATH="$(cd "${GITHUB_EXPORT_REPO_PATH}" && pwd)"
TARGET_DIR_REL="${GITHUB_EXPORT_TARGET_DIR}"
TARGET_DIR_ABS="${REPO_PATH}/${TARGET_DIR_REL}"
BASENAME="$(basename "${SOURCE_XML}")"
TARGET_FILE="${TARGET_DIR_ABS}/${BASENAME}"

mkdir -p "${TARGET_DIR_ABS}"

log "START | source=${SOURCE_XML} | repo=${REPO_PATH} | target_dir=${TARGET_DIR_REL}"

pushd "${REPO_PATH}" >/dev/null

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TARGET_BRANCH="${GITHUB_EXPORT_BRANCH:-$CURRENT_BRANCH}"

if [[ "${CURRENT_BRANCH}" != "${TARGET_BRANCH}" ]]; then
  log "INFO | switching branch from ${CURRENT_BRANCH} to ${TARGET_BRANCH}"
  git checkout "${TARGET_BRANCH}"
fi

cp "${SOURCE_XML}" "${TARGET_FILE}"
log "COPIED | ${SOURCE_XML} -> ${TARGET_FILE}"

git add "${TARGET_DIR_REL}/${BASENAME}"

if git diff --cached --quiet; then
  log "NO_CHANGES | nothing to commit"
  popd >/dev/null
  exit 0
fi

if [[ -z "${GITHUB_EXPORT_COMMIT_MSG}" ]]; then
  GITHUB_EXPORT_COMMIT_MSG="Add translated XML: ${BASENAME}"
fi

git commit -m "${GITHUB_EXPORT_COMMIT_MSG}"
log "COMMIT | message=${GITHUB_EXPORT_COMMIT_MSG}"

if [[ "${GITHUB_EXPORT_PUSH}" == "true" ]]; then
  git push origin "${TARGET_BRANCH}"
  log "PUSH | branch=${TARGET_BRANCH}"
else
  log "SKIP_PUSH | GITHUB_EXPORT_PUSH=false"
fi

popd >/dev/null

log "DONE | exported=${TARGET_FILE}"
echo "Export completed: ${TARGET_FILE}"
