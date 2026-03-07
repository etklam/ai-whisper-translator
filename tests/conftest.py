from unittest.mock import Mock

import pytest


@pytest.fixture
def fake_services():
    return {
        "subtitle_repo": Mock(),
        "translation_client": Mock(),
        "prompt_provider": Mock(),
        "event_sink": Mock(),
    }
