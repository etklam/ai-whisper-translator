#!/usr/bin/env bash
set -euo pipefail

backend="metal"
config="Release"
build_dir="whisper.cpp/build"
clean="false"
source_dir=""
repo_url="https://github.com/ggerganov/whisper.cpp.git"
model="base"
download_model="true"
native="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend)
      backend="$2"
      shift 2
      ;;
    --config)
      config="$2"
      shift 2
      ;;
    --build-dir)
      build_dir="$2"
      shift 2
      ;;
    --source-dir)
      source_dir="$2"
      shift 2
      ;;
    --repo-url)
      repo_url="$2"
      shift 2
      ;;
    --model)
      model="$2"
      shift 2
      ;;
    --no-model)
      download_model="false"
      shift
      ;;
    --no-native)
      native="false"
      shift
      ;;
    --native)
      native="$2"
      shift 2
      ;;
    --clean)
      clean="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--backend cpu|metal] [--config Release|RelWithDebInfo|Debug] [--build-dir PATH] [--source-dir PATH] [--repo-url URL] [--model MODEL] [--no-model] [--no-native|--native true|false] [--clean]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -z "${source_dir}" ]]; then
  source_dir="${repo_root}/whisper.cpp"
fi

need_tool() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required tool: $1"
    return 1
  fi
  return 0
}

missing=0
need_tool git || missing=1
need_tool cmake || missing=1
need_tool make || missing=1

if [[ "${missing}" -ne 0 ]]; then
  echo "Missing required tools. On macOS, install Xcode CLI tools and cmake."
  echo "Suggested:"
  echo "  xcode-select --install"
  echo "  brew install cmake"
  exit 1
fi

if [[ ! -d "${source_dir}" ]]; then
  echo "whisper.cpp not found at ${source_dir}. Cloning from ${repo_url}..."
  git clone "${repo_url}" "${source_dir}"
fi

if [[ "${clean}" == "true" && -d "${build_dir}" ]]; then
  rm -rf "${build_dir}"
fi

cmake_args=(
  -S "${source_dir}"
  -B "${build_dir}"
  -DCMAKE_BUILD_TYPE="${config}"
  -DBUILD_SHARED_LIBS=ON
  -DWHISPER_BUILD_TESTS=OFF
  -DWHISPER_BUILD_EXAMPLES=OFF
  -DWHISPER_BUILD_SERVER=OFF
)

case "${native}" in
  true|on|ON|1)
    cmake_args+=(-DGGML_NATIVE=ON)
    ;;
  false|off|OFF|0)
    cmake_args+=(-DGGML_NATIVE=OFF)
    ;;
  *)
    echo "Unsupported native flag: ${native}. Use true|false."
    exit 1
    ;;
esac

case "${backend}" in
  metal)
    cmake_args+=(-DGGML_METAL=1)
    ;;
  cpu)
    ;;
  *)
    echo "Unsupported backend: ${backend}. Use cpu or metal."
    exit 1
    ;;
esac

echo "Building whisper.cpp (backend=${backend}, config=${config})..."
cmake "${cmake_args[@]}"
cmake --build "${build_dir}" -j

lib_dylib="${build_dir}/src/libwhisper.dylib"
if [[ -f "${lib_dylib}" ]]; then
  echo "Built ${lib_dylib}"
else
  echo "libwhisper.dylib not found at ${lib_dylib}. Check the build output for errors."
  exit 1
fi

if [[ "${download_model}" == "true" ]]; then
  model_dir="${source_dir}/models"
  mkdir -p "${model_dir}"
  echo "Downloading model: ${model}"
  "${source_dir}/models/download-ggml-model.sh" "${model}"
  echo "Model downloaded into ${model_dir}"
fi

echo "Done. You can point the app to:"
echo "  Library: ${lib_dylib}"
echo "  Models: ${source_dir}/models"
