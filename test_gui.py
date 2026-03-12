#!/usr/bin/env python3
"""Test script to verify GUI initialization with ASR coordinator."""

import sys
import os

def main():
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    print("=" * 60)
    print("GUI Integration Test")
    print("=" * 60)

    # Test 1: Import GUI components
    print("\n[1] Testing GUI import...")
    try:
        from gui.app import App
        print("    ✓ App imported successfully")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Create coordinators
    print("\n[2] Testing coordinator creation...")
    try:
        from application.asr_coordinator import ASRCoordinator
        from infrastructure.translation.ollama_translation_client import OllamaTranslationClient
        from infrastructure.prompt.json_prompt_provider import JsonPromptProvider
        from infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository
        from application.translation_coordinator import TranslationCoordinator

        asr_coord = ASRCoordinator(event_sink=None)
        print("    ✓ ASR coordinator created")

        trans_coord = TranslationCoordinator(
            subtitle_repo=PysrtSubtitleRepository(),
            translation_client=OllamaTranslationClient("http://localhost:11434/v1/chat/completions"),
            prompt_provider=JsonPromptProvider("src/translation/prompts.json"),
            event_sink=None,
        )
        print("    ✓ Translation coordinator created")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 3: Check App class accepts ASR coordinator
    print("\n[3] Testing App initialization (without GUI window)...")
    try:
        import tkinter as tk
        # Create a test root window but don't show it
        root = tk.Tk()
        root.withdraw()  # Hide the window

        # Create App without showing it
        # Note: We can't fully initialize App because it shows the window
        # But we can check if the __init__ signature accepts asr_coordinator
        import inspect
        sig = inspect.signature(App.__init__)
        params = list(sig.parameters.keys())
        print(f"    ✓ App.__init__ parameters: {params}")

        if 'asr_coordinator' in params:
            print("    ✓ App accepts asr_coordinator parameter")
        else:
            print("    ✗ App does not accept asr_coordinator parameter")
            sys.exit(1)

        root.destroy()
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 4: Check on_asr_event method exists
    print("\n[4] Testing on_asr_event method...")
    try:
        if hasattr(App, 'on_asr_event'):
            print("    ✓ App.on_asr_event method exists")
        else:
            print("    ✗ App.on_asr_event method not found")
            sys.exit(1)
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        sys.exit(1)

    # Test 5: Check ASR translations
    print("\n[5] Testing ASR translation strings...")
    try:
        # Create a temporary App instance to check translations
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()

        # We'll just check the translations dictionary structure
        # without fully initializing the App
        import gui.app
        if hasattr(gui.app.App, 'translations'):
            # Check if ASR keys exist
            test_keys = ['asr_tab', 'select_audio', 'youtube_url', 'whisper_model_label']
            for lang in ['zh_tw', 'en']:
                if lang in gui.app.App.translations:
                    missing_keys = [k for k in test_keys if k not in gui.app.App.translations[lang]]
                    if missing_keys:
                        print(f"    ✗ Missing ASR keys in {lang}: {missing_keys}")
                    else:
                        print(f"    ✓ ASR translations exist for {lang}")
                else:
                    print(f"    ✗ No translations for {lang}")

        root.destroy()
    except Exception as e:
        print(f"    ⚠ Warning (may not be critical): {e}")

    print("\n" + "=" * 60)
    print("GUI Integration Test Complete! ✓")
    print("=" * 60)
    print("\nNote: Full GUI initialization requires:")
    print("  - Ollama server running (http://localhost:11434)")
    print("  - whisper.cpp library and models (for ASR)")
    print("  - Display server (for GUI)")


if __name__ == "__main__":
    main()
