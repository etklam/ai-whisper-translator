param(
    [ValidateSet("cpu", "cuda", "hip", "vulkan", "openvino")]
    [string]$Backend = "cpu",
    [ValidateSet("Release", "RelWithDebInfo", "Debug")]
    [string]$Config = "Release",
    [string]$BuildDir = "whisper.cpp/build",
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $repoRoot
$sourceDir = Join-Path $repoRoot "whisper.cpp"

if (-not (Test-Path $sourceDir)) {
    throw "whisper.cpp not found at $sourceDir. Ensure the submodule/repo is present."
}

if ($Clean -and (Test-Path $BuildDir)) {
    Remove-Item -Recurse -Force $BuildDir
}

if (-not $env:VSINSTALLDIR -and -not $env:VisualStudioVersion) {
    Write-Host "Tip: use 'Developer PowerShell for VS' so MSVC and CMake are on PATH."
}

$cmakeArgs = @(
    "-S", $sourceDir,
    "-B", $BuildDir,
    "-DBUILD_SHARED_LIBS=ON",
    "-DWHISPER_BUILD_TESTS=OFF",
    "-DWHISPER_BUILD_EXAMPLES=OFF",
    "-DWHISPER_BUILD_SERVER=OFF"
)

switch ($Backend) {
    "cuda"     { $cmakeArgs += "-DGGML_CUDA=1" }
    "hip"      { $cmakeArgs += "-DGGML_HIP=1" }
    "vulkan"   { $cmakeArgs += "-DGGML_VULKAN=1" }
    "openvino" { $cmakeArgs += "-DWHISPER_OPENVINO=1" }
    default    { }
}

& cmake @cmakeArgs
& cmake --build $BuildDir --config $Config -j

$binDll = Join-Path $BuildDir "bin\\whisper.dll"
$dstDll = Join-Path $BuildDir "src\\whisper.dll"

if (Test-Path $binDll) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dstDll) | Out-Null
    Copy-Item $binDll $dstDll -Force
    Write-Host "whisper.dll copied to $dstDll"
} else {
    Write-Host "whisper.dll not found at $binDll. Check the build output for errors."
}
