#!/usr/bin/env bash
#
# init_project.sh — create the DocExtract AI folder structure.
#
# Creates (idempotent — safe to re-run):
#   apps/web/        Next.js frontend        (Phase 9)
#   apps/api/        FastAPI backend         (Phase 2)
#   docker/          Compose setup           (Phase 10)
#   docs/adr/        decision records        (exists, Phase 1)
#   scripts/         utility scripts         (exists, Phase 1)
#   .github/workflows/  CI/CD workflows      (Phase 12)
#
# Empty directories get a .gitkeep file so git tracks them.

set -euo pipefail

# Repository root = directory containing this script's parent.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

DIRECTORIES=(
  "apps/web"
  "apps/api"
  "docker"
  "docs/adr"
  "scripts"
  ".github/workflows"
)

echo "Initializing DocExtract AI project structure in: ${ROOT_DIR}"

for dir in "${DIRECTORIES[@]}"; do
  target="${ROOT_DIR}/${dir}"
  mkdir -p "${target}"
  if [ -z "$(ls -A "${target}" 2>/dev/null)" ]; then
    touch "${target}/.gitkeep"
    echo "  created ${dir}/ (empty, added .gitkeep)"
  else
    echo "  kept    ${dir}/ (already has content)"
  fi
done

echo "Done. Structure ready for Phase 2."
