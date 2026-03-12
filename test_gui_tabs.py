#!/usr/bin/env python3
"""Test script to verify GUI with tabs."""

import sys
import os


def main():
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    print("=" * 60)
    print("GUI Tabs Test")
    print("=" * 60)

    # Test 1: Import App
    print("\n[1] Testing App import...")
    try:
        from gui.app import App
        print("    ✓ App imported successfully")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Check Tab Methods
    print("\n[2] Checking tab creation methods...")
    try:
        if hasattr(App, '_create_translate_tab'):
            print("    ✓ _create_translate_tab method exists")
        else:
            print("    ✗ _create_translate_tab method not found")
            sys.exit(1)

        if hasattr(App, '_create_asr_tab'):
            print("    ✓ _create_asr_tab method exists")
        else:
            print("    ✗ _create_asr_tab method not found")
            sys.exit(1)
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        sys.exit(1)

    # Test 3: Check ASR Methods
    print("\n[3] Checking ASR methods...")
    try:
        asr_methods = [
            'select_audio',
            'browse_model',
            'download_from_youtube',
            'start_asr',
        ]
        for method in asr_methods:
            if hasattr(App, method):
                print(f"    ✓ {method} method exists")
            else:
                print(f"    ✗ {method} method not found")
                sys.exit(1)
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        sys.exit(1)

    # Test 4: Check Notebook
    print("\n[4] Testing Notebook initialization (without GUI window)...")
    try:
        import tkinter as tk
        # Create a test root window but don't show it
        root = tk.Tk()
        root.withdraw()  # Hide window

        # Create minimal App instance to test
        # Note: We can't fully initialize App because it shows window
        # But we can check if the structure is correct
        import gui.app

        # Check if translations have ASR keys
        test_keys = [
            'asr_tab', 'translate_tab',
            'select_audio', 'youtube_url', 'download_from_youtube',
            'whisper_model_label', 'use_gpu', 'gpu_backend',
            'asr_language_label', 'output_format', 'start_asr'
        ]

        for lang in ['zh_tw', 'en']:
            if lang in gui.app.App.translations:
                missing_keys = [k for k in test_keys if k not in gui.app.App.translations[lang]]
                if missing_keys:
                    print(f"    ⚠ Missing ASR keys in {lang}: {missing_keys}")
                else:
                    print(f"    ✓ All ASR translations exist for {lang}")
            else:
                print(f"    ✗ No translations for {lang}")

        root.destroy()
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("GUI Tabs Test Complete! ✓")
    print("=" * 60)
    print("\nNote: Full GUI initialization requires:")
    print("  - Display server (for GUI)")
    print("  - whisper.cpp library and models (for ASR)")


if __name__ == "__main__":
    main()
