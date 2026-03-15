import shutil
import uuid
from pathlib import Path

import pytest

from src.infrastructure.asr.const_me_provider import ConstMeWhisperProvider


def test_const_me_provider_raises_clear_error_when_runtime_dll_is_missing():
    temp_dir = Path(".tmp_test_artifacts") / f"const_me_provider_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        model_path = temp_dir / "ggml-base.bin"
        model_path.write_bytes(b"model")

        provider = ConstMeWhisperProvider(
            model_path=str(model_path),
            runtime_dir=str(temp_dir / "missing-runtime"),
        )

        with pytest.raises(FileNotFoundError, match="Const-me"):
            provider.load_model()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
