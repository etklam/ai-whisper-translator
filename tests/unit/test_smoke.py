from pathlib import Path


def test_fixture_exists():
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    assert (fixtures_dir / "sample_input.srt").exists()
