from speech_to_subtitle.config import load_config, save_config


def test_config_round_trip_and_invalid_choices(tmp_path):
    path = tmp_path / "config.json"
    save_config({"model": "medium", "language": "zh", "srt": False}, path)
    data = load_config(path)
    assert data["model"] == "medium" and data["language"] == "zh" and data["srt"] is False
    path.write_text('{"model":"bad","device":"bad"}', encoding="utf-8")
    data = load_config(path)
    assert data["model"] == "small" and data["device"] == "auto"
