#!/usr/bin/env python3
"""Test script to verify whisper.cpp integration."""

import sys
import os


def main():
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    print("=" * 60)
    print("whisper.cpp Integration Test")
    print("=" * 60)

    # Test 1: Check whisper.cpp directory exists
    print("\n[1] Checking whisper.cpp directory...")
    whisper_cpp_path = os.path.join(os.path.dirname(__file__), 'whisper.cpp')
    if os.path.exists(whisper_cpp_path):
        print(f"    ✓ whisper.cpp directory exists: {whisper_cpp_path}")
        print(
            "    Size: "
            f"{sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, dirnames, filenames in os.walk(whisper_cpp_path) for filename in filenames) / (1024*1024):.1f} MB"
        )
    else:
        print(f"    ✗ whisper.cpp directory not found: {whisper_cpp_path}")
        sys.exit(1)

    # Test 2: Check libwhisper.dylib exists
    print("\n[2] Checking libwhisper.dylib...")
    lib_paths = [
        os.path.join(whisper_cpp_path, "build/src/libwhisper.dylib"),
        os.path.join(whisper_cpp_path, "build/src/libwhisper.1.dylib"),
    ]
    lib_found = False
    for lib_path in lib_paths:
        if os.path.exists(lib_path):
            print(f"    ✓ libwhisper found: {lib_path}")
            lib_found = True
            break

    if not lib_found:
        print("    ✗ libwhisper.dylib not found in whisper.cpp/build/src/")
        sys.exit(1)

    # Test 3: Check models exist
    print("\n[3] Checking Whisper models...")
    models_dir = os.path.join(whisper_cpp_path, "models")
    if os.path.exists(models_dir):
        models = [f for f in os.listdir(models_dir) if f.endswith('.bin')]
        if models:
            print(f"    ✓ Found {len(models)} model files:")
            for model in models[:5]:  # Show first 5
                size = os.path.getsize(os.path.join(models_dir, model)) / (1024*1024)
                print(f"      - {model} ({size:.1f} MB)")
            if len(models) > 5:
                print(f"      ... and {len(models) - 5} more")
        else:
            print(f"    ⚠ No model files found in {models_dir}")
    else:
        print("    ✗ models directory not found")
        sys.exit(1)

    # Test 4: Import and create WhisperWrapper
    print("\n[4] Testing WhisperWrapper initialization...")
    try:
        from asr.whisper_wrapper import WhisperWrapper
        # Use default path (should auto-detect)
        wrapper = WhisperWrapper(library_path=None)
        print("    ✓ WhisperWrapper initialized successfully")
        print(f"      - Library loaded from: {wrapper.lib._name}")

        # Get version
        version = wrapper.get_version()
        print(f"      - Whisper version: {version}")
    except Exception as e:
        print(f"    ✗ Failed to initialize WhisperWrapper: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 5: Test Transcriber with tiny model
    print("\n[5] Testing Transcriber initialization...")
    try:
        from asr.whisper_transcriber import Transcriber

        # Use a test model
        test_model = os.path.join(models_dir, "for-tests-ggml-tiny.bin")
        if os.path.exists(test_model):
            transcriber = Transcriber(
                model_path=test_model,
                use_gpu=False,
                gpu_backend="cpu",
            )
            print(f"    ✓ Transcriber created with test model: {os.path.basename(test_model)}")

            # Try to load model
            print("    Loading model...")
            transcriber.load_model()
            print("    ✓ Model loaded successfully")

            # Get system info
            sys_info = wrapper.get_system_info()
            print(f"    ✓ System info: {sys_info}")

        else:
            print(f"    ⚠ Test model not found: {test_model}")

    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("whisper.cpp Integration Test Complete! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
