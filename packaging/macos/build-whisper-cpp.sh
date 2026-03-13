#!/usr/bin/env bash
set -euo pipefail

backend="cpu"
config="Release"
build_dir="whisper.cpp/build"
clean="false"

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
    --clean)
      clean="true"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--backend cpu|metal] [--config Release|RelWithDebInfo|Debug] [--build-dir PATH] [--clean]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_dir="${repo_root}/whisper.cpp"

if [[ ! -d "${source_dir}" ]]; then
  echo "whisper.cpp not found at ${source_dir}. Ensure the submodule/repo is present."
  exit 1
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

cmake "${cmake_args[@]}"
cmake --build "${build_dir}" -j

lib_dylib="${build_dir}/src/libwhisper.dylib"
if [[ -f "${lib_dylib}" ]]; then
  echo "Built ${lib_dylib}"
else
  echo "libwhisper.dylib not found at ${lib_dylib}. Check the build output for errors."
fi
