param(
    [string]$Backend = "",
    [ValidateSet("Release", "RelWithDebInfo", "Debug")]
    [string]$Config = "Release",
    [string]$Model = "",
    [switch]$SkipModel,
    [bool]$WriteConfig = $true,
    [switch]$Clean,
    [string]$ConfigPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-LastNativeCommandSucceeded {
    $lastExitCodeVar = Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue
    if ($null -eq $lastExitCodeVar) {
        return $true
    }
    return $lastExitCodeVar.Value -eq 0
}

function Initialize-VulkanSdkEnvironment {
    param(
        [string]$HelperScriptPath
    )

    $rawResult = & python $HelperScriptPath --resolve-windows-vulkan-sdk
    if (-not (Test-LastNativeCommandSucceeded)) {
        throw "Unable to resolve a valid Windows Vulkan SDK. Checked VULKAN_SDK, VK_SDK_PATH, and C:\VulkanSDK\*."
    }

    $vulkanInfo = $rawResult | ConvertFrom-Json
    if (-not $vulkanInfo.sdk_dir -or -not $vulkanInfo.bin_dir) {
        throw "Vulkan SDK helper returned incomplete metadata."
    }

    $env:VULKAN_SDK = $vulkanInfo.sdk_dir
    $currentPathEntries = @($env:Path -split ';' | Where-Object { $_ })
    if ($currentPathEntries -notcontains $vulkanInfo.bin_dir) {
        $env:Path = "$($vulkanInfo.bin_dir);$env:Path"
    }
}

function Get-PaddedMenuLine {
    param(
        [string]$Text,
        [int]$Width
    )

    $safeText = if ($null -eq $Text) { "" } else { $Text }
    if ($safeText.Length -ge $Width) {
        return $safeText.Substring(0, $Width)
    }
    return $safeText.PadRight($Width)
}

function Clear-MenuRegion {
    param(
        [int]$Top,
        [int]$Height,
        [int]$Width
    )

    $bufferHeight = [Console]::BufferHeight
    if ($bufferHeight -le 0) {
        return
    }

    $safeTop = [Math]::Max(0, [Math]::Min($Top, $bufferHeight - 1))
    $safeWidth = [Math]::Max(1, [Math]::Min($Width, [Console]::BufferWidth))
    $blankLine = " " * $safeWidth

    for ($lineOffset = 0; $lineOffset -lt $Height; $lineOffset++) {
        $targetTop = $safeTop + $lineOffset
        if ($targetTop -ge $bufferHeight) {
            break
        }
        [Console]::SetCursorPosition(0, $targetTop)
        [Console]::Write($blankLine)
    }
}

function Select-MenuOption {
    param(
        [string]$Title,
        [array]$Options,
        [int]$DefaultIndex = 0
    )

    if (-not $Options -or $Options.Count -eq 0) {
        throw "No options provided for menu: $Title"
    }

    $index = [Math]::Max(0, [Math]::Min($DefaultIndex, $Options.Count - 1))
    $cursorTop = [Console]::CursorTop
    $menuHeight = $Options.Count + 3
    $menuWidth = 0
    foreach ($option in $Options) {
        $labelWidth = if ($null -eq $option.Label) { 0 } else { $option.Label.Length }
        $menuWidth = [Math]::Max($menuWidth, $labelWidth + 4)
    }
    $menuWidth = [Math]::Max([Math]::Max($menuWidth, $Title.Length), "Use Up/Down to choose, Enter to confirm".Length)
    $menuWidth = [Math]::Min([Math]::Max($menuWidth + 2, 24), [Math]::Max(1, [Console]::BufferWidth))
    $useFullRedraw = $false

    while ($true) {
        if ($useFullRedraw) {
            Clear-Host
            Write-Host $Title
            Write-Host "Use Up/Down to choose, Enter to confirm"
            foreach ($i in 0..($Options.Count - 1)) {
                $prefix = if ($i -eq $index) { ">" } else { " " }
                Write-Host ("{0} {1}" -f $prefix, $Options[$i].Label)
            }
        } else {
            try {
                Clear-MenuRegion -Top $cursorTop -Height $menuHeight -Width $menuWidth
                [Console]::SetCursorPosition(0, $cursorTop)
                Write-Host (Get-PaddedMenuLine -Text $Title -Width $menuWidth)
                Write-Host (Get-PaddedMenuLine -Text "Use Up/Down to choose, Enter to confirm" -Width $menuWidth)
                foreach ($i in 0..($Options.Count - 1)) {
                    $prefix = if ($i -eq $index) { ">" } else { " " }
                    $line = "{0} {1}" -f $prefix, $Options[$i].Label
                    Write-Host (Get-PaddedMenuLine -Text $line -Width $menuWidth)
                }
            } catch {
                $useFullRedraw = $true
                continue
            }
        }

        $key = [Console]::ReadKey($true)
        if ($key.Key -eq [ConsoleKey]::UpArrow) {
            if ($index -gt 0) { $index-- } else { $index = $Options.Count - 1 }
            continue
        }
        if ($key.Key -eq [ConsoleKey]::DownArrow) {
            if ($index -lt ($Options.Count - 1)) { $index++ } else { $index = 0 }
            continue
        }
        if ($key.Key -eq [ConsoleKey]::Enter) {
            if ($useFullRedraw) {
                Write-Host ""
            } else {
                try {
                    $safeCursorTop = [Math]::Min($cursorTop + $Options.Count + 2, [Console]::BufferHeight - 1)
                    [Console]::SetCursorPosition(0, $safeCursorTop)
                } catch {
                    Write-Host ""
                }
            }
            return $Options[$index].Value
        }
    }
}

function Show-Usage {
    Write-Host "Usage: setup-whisper-cpp.ps1 [-Backend cpu|cuda|vulkan|openvino] [-Config Release|RelWithDebInfo|Debug] [-Model MODEL] [-SkipModel] [-WriteConfig `$true|`$false] [-Clean] [-ConfigPath PATH]"
    Write-Host "Windows ASR provider target: Const-me/Whisper"
    Write-Host "Backend options:"
    Write-Host "  CPU (no GPU)"
    Write-Host "  CUDA (NVIDIA)"
    Write-Host "  Vulkan (AMD)"
    Write-Host "  OpenVINO (Intel)"
    Write-Host "Use Up/Down to choose, Enter to confirm"
    Write-Host "Available environments:"
    Write-Host "Installed models:"
    Write-Host "Available download models:"
}

if ($args -contains "-Help" -or $args -contains "--help" -or $args -contains "-h") {
    Show-Usage
    exit 0
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $repoRoot
$sourceDir = Join-Path $repoRoot "whisper.cpp"
$buildScript = Join-Path $PSScriptRoot "build-whisper-cpp.ps1"
$helperScript = Join-Path $repoRoot "packaging\update_asr_config.py"
$repoUrl = "https://github.com/ggerganov/whisper.cpp.git"
$modelDir = Join-Path $sourceDir "models"
$resolvedConfigPath = if ([string]::IsNullOrWhiteSpace($ConfigPath)) { Join-Path $repoRoot ".config" } else { $ConfigPath }
$sourceReady = Test-Path (Join-Path $sourceDir "CMakeLists.txt")

if ([string]::IsNullOrWhiteSpace($Backend)) {
    $Backend = Select-MenuOption -Title "Available environments:" -Options @(
        @{ Label = "CPU (no GPU)"; Value = "cpu" }
        @{ Label = "CUDA (NVIDIA)"; Value = "cuda" }
        @{ Label = "Vulkan (AMD)"; Value = "vulkan" }
        @{ Label = "OpenVINO (Intel)"; Value = "openvino" }
    ) -DefaultIndex 0
} else {
    $Backend = (& python $helperScript --resolve-backend $Backend --platform windows --arch AMD64).Trim()
}
if (-not (Test-LastNativeCommandSucceeded)) {
    throw "Unsupported backend selection."
}

if ($Backend -eq "vulkan") {
    Initialize-VulkanSdkEnvironment -HelperScriptPath $helperScript
}

if (-not $sourceReady) {
    & git submodule update --init --recursive -- whisper.cpp
    $sourceReady = Test-Path (Join-Path $sourceDir "CMakeLists.txt")
}

if (-not $sourceReady) {
    $backupDir = "{0}.broken.{1}" -f $sourceDir, (Get-Date -Format "yyyyMMddHHmmss")
    $modelsBackupDir = Join-Path $repoRoot (".whisper-models-backup-{0}" -f (Get-Date -Format "yyyyMMddHHmmss"))
    if (Test-Path $modelDir) {
        Move-Item -Path $modelDir -Destination $modelsBackupDir
    }
    if (Test-Path $sourceDir) {
        Move-Item -Path $sourceDir -Destination $backupDir
    }
    & git clone $repoUrl $sourceDir
    if (-not (Test-LastNativeCommandSucceeded)) {
        throw "Failed to clone whisper.cpp from $repoUrl"
    }
    if (Test-Path $modelsBackupDir) {
        $restoredModelDir = Join-Path $sourceDir "models"
        New-Item -ItemType Directory -Force -Path $restoredModelDir | Out-Null
        Get-ChildItem -Force $modelsBackupDir | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $restoredModelDir -Force
        }
        Remove-Item -Path $modelsBackupDir -Force
    }
    $sourceReady = Test-Path (Join-Path $sourceDir "CMakeLists.txt")
}

if (-not $sourceReady) {
    throw "whisper.cpp source is missing at $sourceDir after recovery."
}

& $buildScript -Backend $Backend -Config $Config -Clean:$Clean

if ([string]::IsNullOrWhiteSpace($Model)) {
    $installedModels = @((& python $helperScript --list-models --models-dir $modelDir) | ForEach-Object { $_.Trim() }) | Where-Object { $_ }
    $installedSection = $false
    $downloadSection = $false
    $modelOptions = New-Object System.Collections.Generic.List[object]
    foreach ($line in $installedModels) {
        if ($line -eq "Installed models:") {
            $installedSection = $true
            $downloadSection = $false
            continue
        }
        if ($line -eq "Available download models:") {
            $installedSection = $false
            $downloadSection = $true
            continue
        }
        if ($installedSection) {
            $modelOptions.Add(@{ Label = "$line [installed]"; Value = $line })
            continue
        }
        if ($downloadSection) {
            $modelOptions.Add(@{ Label = "$line [download]"; Value = $line })
        }
    }
    $defaultIndex = 0
    for ($i = 0; $i -lt $modelOptions.Count; $i++) {
        if ($modelOptions[$i].Value -eq "base") {
            $defaultIndex = $i
            break
        }
    }
    $Model = Select-MenuOption -Title "Available models:" -Options $modelOptions -DefaultIndex $defaultIndex
} else {
    $Model = (& python $helperScript --resolve-model $Model).Trim()
}
if (-not (Test-LastNativeCommandSucceeded)) {
    throw "Unsupported model selection."
}

$modelPath = Join-Path $modelDir ("ggml-{0}.bin" -f $Model)

if (-not $SkipModel) {
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
    if (-not (Test-Path $modelPath)) {
        $downloadUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.bin?download=true"
        Write-Host "Downloading model $Model from $downloadUrl"
        Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $modelPath
    }
}

if (-not (Test-Path $modelPath)) {
    throw "Model file not found at $modelPath"
}

if ($WriteConfig) {
    & python $helperScript --config $resolvedConfigPath --model-path $modelPath --backend $Backend --platform windows
}

Write-Host "Setup complete."
Write-Host "Windows ASR provider target: Const-me/Whisper"
Write-Host "Backend: $Backend"
Write-Host "Model: $modelPath"
Write-Host "Config: $resolvedConfigPath"
