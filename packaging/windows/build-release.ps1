Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$specPath = Join-Path $repoRoot "packaging/windows/pyinstaller.spec"

Push-Location $repoRoot
try {
    uv run --with pyinstaller pyinstaller --noconfirm --clean $specPath
}
finally {
    Pop-Location
}
