# init_project.ps1 — create the DocExtract AI folder structure (Windows).
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
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\init_project.ps1

$ErrorActionPreference = "Stop"

# Repository root = parent directory of this script's folder.
$RootDir = Split-Path -Parent $PSScriptRoot

$Directories = @(
    "apps/web",
    "apps/api",
    "docker",
    "docs/adr",
    "scripts",
    ".github/workflows"
)

Write-Host "Initializing DocExtract AI project structure in: $RootDir"

foreach ($Dir in $Directories) {
    $Target = Join-Path $RootDir $Dir
    New-Item -ItemType Directory -Path $Target -Force | Out-Null

    $IsEmpty = -not (Get-ChildItem -Path $Target -Force | Select-Object -First 1)
    if ($IsEmpty) {
        New-Item -ItemType File -Path (Join-Path $Target ".gitkeep") | Out-Null
        Write-Host "  created $Dir/ (empty, added .gitkeep)"
    }
    else {
        Write-Host "  kept    $Dir/ (already has content)"
    }
}

Write-Host "Done. Structure ready for Phase 2."
