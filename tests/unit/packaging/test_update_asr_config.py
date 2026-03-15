import importlib.util
import importlib.util
import json
import shutil
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "packaging" / "update_asr_config.py"
TEMP_ROOT = Path.home() / ".codex" / "memories"


def load_module():
    spec = importlib.util.spec_from_file_location("update_asr_config", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_test_dir(name: str) -> Path:
    path = TEMP_ROOT / f"{name}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_merge_asr_settings_preserves_non_asr_fields():
    module = load_module()
    model_path = Path("C:/tmp/whisper.cpp/models/ggml-base.bin")

    payload = module.merge_asr_settings(
        {"model_name": "keep-me", "translation_engine_key": "ollama"},
        model_path=model_path,
        backend="cuda",
    )

    assert payload["model_name"] == "keep-me"
    assert payload["translation_engine_key"] == "ollama"
    assert payload["asr_model_path"] == str(model_path)
    assert payload["gpu_backend"] == "cuda"
    assert payload["use_gpu"] is True


def test_merge_asr_settings_sets_windows_provider_to_const_me():
    module = load_module()

    payload = module.merge_asr_settings(
        {},
        model_path=Path("C:/tmp/model.bin"),
        backend="cpu",
        platform_name="windows",
    )

    assert payload["asr_provider"] == "const_me"


def test_merge_asr_settings_sets_use_gpu_false_for_cpu():
    module = load_module()
    payload = module.merge_asr_settings({}, model_path=Path("/tmp/model.bin"), backend="cpu")

    assert payload["gpu_backend"] == "cpu"
    assert payload["use_gpu"] is False


def test_normalize_installed_models_returns_sorted_model_keys():
    module = load_module()
    installed = module.normalize_installed_models(
        [
            "ggml-large-v3.bin",
            "ggml-base.bin",
            "ignore.txt",
        ]
    )
    assert installed == ["base", "large-v3"]


def test_resolve_model_choice_defaults_to_base_on_empty_input():
    module = load_module()

    choice = module.resolve_model_choice("   ")

    assert choice == "base"


def test_resolve_model_choice_rejects_unknown_model():
    module = load_module()

    try:
        module.resolve_model_choice("weird-model")
    except ValueError as exc:
        assert "Unsupported model" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported model")


def test_supported_backends_for_windows():
    module = load_module()

    backends = module.supported_backends_for_platform("windows", "AMD64")

    assert backends == ["cpu", "cuda", "vulkan", "openvino"]


def test_supported_backends_for_macos_arm64():
    module = load_module()

    backends = module.supported_backends_for_platform("darwin", "arm64")

    assert backends == ["metal", "cpu"]


def test_resolve_backend_choice_defaults_windows_to_cpu():
    module = load_module()

    backend = module.resolve_backend_choice("   ", "windows", "AMD64")

    assert backend == "cpu"


def test_resolve_backend_choice_defaults_macos_arm64_to_metal():
    module = load_module()

    backend = module.resolve_backend_choice("   ", "darwin", "arm64")

    assert backend == "metal"


def test_resolve_backend_choice_rejects_invalid_platform_backend():
    module = load_module()

    try:
        module.resolve_backend_choice("metal", "windows", "AMD64")
    except ValueError as exc:
        assert "Unsupported backend" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported backend")


def test_resolve_windows_vulkan_sdk_prefers_valid_environment_variable():
    module = load_module()
    temp_dir = make_test_dir("vulkan-sdk-env")
    try:
        sdk_root = temp_dir / "VulkanSDK"
        invalid_sdk = sdk_root / "1.4.300.0"
        invalid_sdk.mkdir(parents=True)
        sdk_dir = sdk_root / "1.4.341.1"
        (sdk_dir / "Include" / "vulkan").mkdir(parents=True)
        (sdk_dir / "Lib").mkdir(parents=True)
        (sdk_dir / "Bin").mkdir(parents=True)
        (sdk_dir / "Include" / "vulkan" / "vulkan.h").write_text("", encoding="utf-8")
        (sdk_dir / "Lib" / "vulkan-1.lib").write_text("", encoding="utf-8")
        (sdk_dir / "Bin" / "glslc.exe").write_text("", encoding="utf-8")

        resolved = module.resolve_windows_vulkan_sdk(
            env={"VULKAN_SDK": str(sdk_dir)},
            sdk_root=sdk_root,
        )

        assert resolved["sdk_dir"] == str(sdk_dir)
        assert resolved["source"] == "VULKAN_SDK"
        assert resolved["bin_dir"] == str(sdk_dir / "Bin")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolve_windows_vulkan_sdk_falls_back_to_highest_valid_version():
    module = load_module()
    temp_dir = make_test_dir("vulkan-sdk-scan")
    try:
        sdk_root = temp_dir / "VulkanSDK"
        older_sdk = sdk_root / "1.4.300.0"
        newer_sdk = sdk_root / "1.4.341.1"

        for sdk_dir in (older_sdk, newer_sdk):
            (sdk_dir / "Include" / "vulkan").mkdir(parents=True)
            (sdk_dir / "Lib").mkdir(parents=True)
            (sdk_dir / "Bin").mkdir(parents=True)
            (sdk_dir / "Include" / "vulkan" / "vulkan.h").write_text("", encoding="utf-8")
            (sdk_dir / "Lib" / "vulkan-1.lib").write_text("", encoding="utf-8")
            (sdk_dir / "Bin" / "glslc.exe").write_text("", encoding="utf-8")

        resolved = module.resolve_windows_vulkan_sdk(
            env={},
            sdk_root=sdk_root,
        )

        assert resolved["sdk_dir"] == str(newer_sdk)
        assert resolved["source"] == "scan"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolve_windows_vulkan_sdk_cli_emits_json(capsys):
    module = load_module()
    temp_dir = make_test_dir("vulkan-sdk-cli")
    try:
        sdk_dir = temp_dir / "VulkanSDK" / "1.4.341.1"
        (sdk_dir / "Include" / "vulkan").mkdir(parents=True)
        (sdk_dir / "Lib").mkdir(parents=True)
        (sdk_dir / "Bin").mkdir(parents=True)
        (sdk_dir / "Include" / "vulkan" / "vulkan.h").write_text("", encoding="utf-8")
        (sdk_dir / "Lib" / "vulkan-1.lib").write_text("", encoding="utf-8")
        (sdk_dir / "Bin" / "glslc.exe").write_text("", encoding="utf-8")

        exit_code = module.main(
            [
                "--resolve-windows-vulkan-sdk",
                "--sdk-root",
                str(temp_dir / "VulkanSDK"),
            ]
        )

        captured = capsys.readouterr()
        payload = json.loads(captured.out)

        assert exit_code == 0
        assert payload["sdk_dir"] == str(sdk_dir)
        assert payload["bin_dir"] == str(sdk_dir / "Bin")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_windows_setup_help_mentions_backend_brands():
    script_path = REPO_ROOT / "packaging" / "windows" / "setup-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert "Const-me/Whisper" in content
    assert "CPU (no GPU)" in content
    assert "CUDA (NVIDIA)" in content
    assert "Vulkan (AMD)" in content
    assert "OpenVINO (Intel)" in content
    assert "Installed models:" in content
    assert "Available download models:" in content
    assert "Available environments:" in content
    assert "Use Up/Down to choose, Enter to confirm" in content
    assert "& $buildScript -Backend $Backend -Config $Config" in content
    assert "function Select-MenuOption" in content
    assert "function Clear-MenuRegion" in content
    assert "function Get-PaddedMenuLine" in content
    assert '$Model = Select-MenuOption' in content
    assert '$Backend = Select-MenuOption' in content
    assert '$menuHeight = $Options.Count + 3' in content
    assert '$useFullRedraw = $false' in content
    assert "Clear-MenuRegion -Top $cursorTop -Height $menuHeight -Width $menuWidth" in content
    assert '$useFullRedraw = $true' in content
    assert "Clear-Host" in content
    assert '$safeCursorTop = [Math]::Min($cursorTop + $Options.Count + 2, [Console]::BufferHeight - 1)' in content
    assert '$sourceReady = Test-Path (Join-Path $sourceDir "CMakeLists.txt")' in content
    assert 'git submodule update --init --recursive -- whisper.cpp' in content
    assert 'git clone $repoUrl $sourceDir' in content
    assert '$backupDir = "{0}.broken.' in content

    build_script_path = REPO_ROOT / "packaging" / "windows" / "build-whisper-cpp.ps1"
    build_content = build_script_path.read_text(encoding="utf-8")
    assert 'Join-Path $BuildDir "bin\\\\$Config"' in build_content
    assert 'Get-ChildItem -Path $binDir -Filter "*.dll"' in build_content
    assert 'throw "CMake configure failed for backend' in build_content
    assert 'Vulkan backend requires a valid SDK from VULKAN_SDK, VK_SDK_PATH, or C:\\VulkanSDK\\*' in build_content
    assert "--resolve-windows-vulkan-sdk" in build_content
    assert '$env:VULKAN_SDK = $vulkanInfo.sdk_dir' in build_content
    assert '$env:Path = "$($vulkanInfo.bin_dir);$env:Path"' in build_content
    assert "C:\\VulkanSDK\\*" in build_content
    assert "--resolve-windows-vulkan-sdk" in content
    assert '$env:VULKAN_SDK = $vulkanInfo.sdk_dir' in content
    assert '$env:Path = "$($vulkanInfo.bin_dir);$env:Path"' in content


def test_windows_setup_avoids_three_argument_math_max():
    script_path = REPO_ROOT / "packaging" / "windows" / "setup-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert '[Math]::Max($menuWidth, $Title.Length, "Use Up/Down to choose, Enter to confirm".Length)' not in content


def test_windows_setup_guards_last_exit_code_in_strict_mode():
    script_path = REPO_ROOT / "packaging" / "windows" / "setup-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert "function Test-LastNativeCommandSucceeded" in content
    assert "Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue" in content
    assert "if (-not (Test-LastNativeCommandSucceeded))" in content
    assert "if ($LASTEXITCODE -ne 0)" not in content


def test_windows_build_script_fails_fast_after_native_command_errors():
    script_path = REPO_ROOT / "packaging" / "windows" / "build-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert 'function Test-LastNativeCommandSucceeded' in content
    assert '& cmake @cmakeArgs' in content
    assert '& cmake --build $BuildDir --config $Config' in content
    assert 'if (-not (Test-LastNativeCommandSucceeded)) {' in content
    assert 'throw "CMake build failed for backend' in content


def test_windows_build_script_mentions_backend_specific_whisper_dll_names():
    script_path = REPO_ROOT / "packaging" / "windows" / "build-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert "whisper-cuda.dll" in content
    assert "whisper-vulkan.dll" in content
    assert "whisper-cpu.dll" in content


def test_windows_build_script_avoids_parallel_flag_for_msvc_exit_code_bug():
    script_path = REPO_ROOT / "packaging" / "windows" / "build-whisper-cpp.ps1"
    content = script_path.read_text(encoding="utf-8")
    assert '& cmake --build $BuildDir --config $Config -j' not in content
    assert '& cmake --build $BuildDir --config $Config' in content


def test_macos_setup_defaults_model_base():
    script_path = REPO_ROOT / "packaging" / "macos" / "setup-whisper-cpp.sh"
    content = script_path.read_text(encoding="utf-8")
    assert 'default_model="base"' in content
    assert "metal (Apple Silicon/Apple GPU)" in content
    assert "Installed models:" in content
    assert "Available download models:" in content
    assert "Available environments:" in content
    assert 'Choose environment/backend (default: ${default_backend})' in content
    assert 'git clone "${repo_url}" "${source_dir}"' in content
    assert 'backup_dir="${source_dir}.broken.' in content


def test_macos_build_script_mentions_backend_specific_whisper_dylib_names():
    script_path = REPO_ROOT / "packaging" / "macos" / "build-whisper-cpp.sh"
    content = script_path.read_text(encoding="utf-8")
    assert "libwhisper-metal.dylib" in content
    assert "libwhisper-cpu.dylib" in content
