from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from collections.abc import Mapping
from pathlib import Path

from src.infrastructure.asr.providers import resolve_asr_provider


GPU_BACKENDS = {"metal", "cuda", "vulkan", "openvino"}
SUPPORTED_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
    "turbo",
]
WINDOWS_BACKENDS = ["cpu", "cuda", "vulkan", "openvino"]
MACOS_BACKENDS = ["metal", "cpu"]


def supported_backends_for_platform(platform_name: str, arch: str) -> list[str]:
    normalized_platform = (platform_name or "").strip().lower()
    normalized_arch = (arch or "").strip().lower()
    if normalized_platform.startswith("win"):
        return WINDOWS_BACKENDS.copy()
    if normalized_platform == "darwin":
        return MACOS_BACKENDS.copy()
    if normalized_platform == "macos":
        return MACOS_BACKENDS.copy()
    raise ValueError(f"Unsupported platform for backend selection: {platform_name}/{arch}")


def default_backend_for_platform(platform_name: str, arch: str) -> str:
    normalized_platform = (platform_name or "").strip().lower()
    normalized_arch = (arch or "").strip().lower()
    if normalized_platform.startswith("win"):
        return "cpu"
    if normalized_platform in {"darwin", "macos"}:
        return "metal" if normalized_arch == "arm64" else "cpu"
    raise ValueError(f"Unsupported platform for backend selection: {platform_name}/{arch}")


def resolve_backend_choice(raw_value: str | None, platform_name: str, arch: str) -> str:
    supported = supported_backends_for_platform(platform_name, arch)
    candidate = (raw_value or "").strip() or default_backend_for_platform(platform_name, arch)
    if candidate not in supported:
        raise ValueError(f"Unsupported backend: {candidate}")
    return candidate


def is_valid_windows_vulkan_sdk(sdk_dir: str | Path) -> bool:
    path = Path(sdk_dir)
    return (
        path.is_dir()
        and (path / "Include" / "vulkan" / "vulkan.h").is_file()
        and (path / "Lib" / "vulkan-1.lib").is_file()
        and (path / "Bin" / "glslc.exe").is_file()
    )


def parse_windows_vulkan_sdk_version(name: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in name.split("."))
    except ValueError:
        return tuple()


def resolve_windows_vulkan_sdk(
    env: Mapping[str, str] | None = None,
    sdk_root: str | Path = Path("C:/VulkanSDK"),
) -> dict[str, str]:
    resolved_env = env if env is not None else os.environ
    for variable_name in ("VULKAN_SDK", "VK_SDK_PATH"):
        candidate = (resolved_env.get(variable_name) or "").strip()
        if candidate and is_valid_windows_vulkan_sdk(candidate):
            sdk_dir = Path(candidate)
            return {
                "sdk_dir": str(sdk_dir),
                "bin_dir": str(sdk_dir / "Bin"),
                "include_dir": str(sdk_dir / "Include"),
                "lib_dir": str(sdk_dir / "Lib"),
                "source": variable_name,
            }

    root = Path(sdk_root)
    candidates: list[tuple[tuple[int, ...], Path]] = []
    if root.is_dir():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            version = parse_windows_vulkan_sdk_version(child.name)
            if not version:
                continue
            if is_valid_windows_vulkan_sdk(child):
                candidates.append((version, child))

    if not candidates:
        raise ValueError(
            "Unable to find a valid Windows Vulkan SDK. Checked VULKAN_SDK, VK_SDK_PATH, and C:\\VulkanSDK\\*."
        )

    _, sdk_dir = max(candidates, key=lambda item: item[0])
    return {
        "sdk_dir": str(sdk_dir),
        "bin_dir": str(sdk_dir / "Bin"),
        "include_dir": str(sdk_dir / "Include"),
        "lib_dir": str(sdk_dir / "Lib"),
        "source": "scan",
    }


def normalize_installed_models(file_names: list[str]) -> list[str]:
    models: list[str] = []
    for file_name in file_names:
        if not (file_name.startswith("ggml-") and file_name.endswith(".bin")):
            continue
        models.append(file_name[len("ggml-") : -len(".bin")])
    return sorted(set(models))


def find_installed_models(models_dir: str | Path) -> list[str]:
    path = Path(models_dir)
    if not path.is_dir():
        return []
    return normalize_installed_models([item.name for item in path.iterdir() if item.is_file()])


def downloadable_models(installed_models: list[str]) -> list[str]:
    installed = set(installed_models)
    return [model for model in SUPPORTED_MODELS if model not in installed]


def resolve_model_choice(raw_value: str | None) -> str:
    candidate = (raw_value or "").strip() or "base"
    if candidate not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model: {candidate}")
    return candidate


def merge_asr_settings(
    payload: dict[str, object],
    model_path: str | Path,
    backend: str,
    platform_name: str | None = None,
) -> dict[str, object]:
    merged = payload.copy()
    merged["asr_model_path"] = str(Path(model_path))
    merged["gpu_backend"] = backend
    merged["use_gpu"] = backend in GPU_BACKENDS
    merged["asr_provider"] = resolve_asr_provider("auto", platform_name or platform.system())
    return merged


def update_asr_settings(
    config_path: str | Path,
    model_path: str | Path,
    backend: str,
    platform_name: str | None = None,
) -> Path:
    resolved_model_path = Path(model_path).expanduser().resolve()
    if not resolved_model_path.is_file():
        raise FileNotFoundError(f"Whisper model file not found: {resolved_model_path}")

    resolved_config_path = Path(config_path).expanduser().resolve()
    payload: dict[str, object] = {}
    if resolved_config_path.exists():
        with resolved_config_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            payload = loaded.copy()

    merged = merge_asr_settings(
        payload=payload,
        model_path=resolved_model_path,
        backend=backend,
        platform_name=platform_name,
    )

    resolved_config_path.parent.mkdir(parents=True, exist_ok=True)
    with resolved_config_path.open("w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=True, indent=2, sort_keys=True)
    return resolved_config_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update ASR settings in the app .config file.")
    parser.add_argument("--config", help="Path to the app .config file.")
    parser.add_argument("--model-path", help="Absolute or relative path to the model file.")
    parser.add_argument(
        "--backend",
        choices=["cpu", "metal", "cuda", "vulkan", "openvino"],
        help="Whisper backend written into the config.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print installed and downloadable model lists for a models directory.",
    )
    parser.add_argument(
        "--models-dir",
        help="Directory containing ggml model files when using --list-models.",
    )
    parser.add_argument(
        "--resolve-model",
        help="Normalize and validate a model selection. Empty input resolves to base.",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Print supported backends for the current or requested platform.",
    )
    parser.add_argument("--platform", dest="platform_name", help="Platform name override for backend selection.")
    parser.add_argument("--arch", help="Architecture override for backend selection.")
    parser.add_argument("--resolve-backend", help="Normalize and validate a backend selection.")
    parser.add_argument(
        "--resolve-windows-vulkan-sdk",
        action="store_true",
        help="Resolve a valid Windows Vulkan SDK from environment variables or C:/VulkanSDK/*.",
    )
    parser.add_argument(
        "--sdk-root",
        help="Override the Vulkan SDK root directory when resolving a Windows Vulkan SDK.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    platform_name = args.platform_name or platform.system()
    arch = args.arch or platform.machine()
    if args.list_backends:
        print("Available environments:")
        for backend in supported_backends_for_platform(platform_name, arch):
            print(backend)
        return 0
    if args.resolve_backend is not None:
        try:
            print(resolve_backend_choice(args.resolve_backend, platform_name, arch))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    if args.resolve_windows_vulkan_sdk:
        try:
            payload = resolve_windows_vulkan_sdk(sdk_root=args.sdk_root or Path("C:/VulkanSDK"))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    if args.list_models:
        installed = find_installed_models(args.models_dir or ".")
        print("Installed models:")
        for model in installed:
            print(model)
        print("Available download models:")
        for model in downloadable_models(installed):
            print(model)
        return 0
    if args.resolve_model is not None:
        try:
            print(resolve_model_choice(args.resolve_model))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    if not args.config or not args.model_path or not args.backend:
        raise SystemExit("--config, --model-path, and --backend are required unless using --list-models or --resolve-model")
    config_path = update_asr_settings(
        config_path=args.config,
        model_path=args.model_path,
        backend=args.backend,
        platform_name=platform_name,
    )
    print(f"Updated ASR config: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
