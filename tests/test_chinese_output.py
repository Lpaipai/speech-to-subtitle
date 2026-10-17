# 2026/10/01 18:15:08 by liaoweipeng1
import json
import sys
from types import SimpleNamespace

import pytest

from speech_to_subtitle.config import load_config, save_config
from speech_to_subtitle.formats import export_result
from speech_to_subtitle.models import TranscribeOptions
from speech_to_subtitle.transcriber import transcribe


@pytest.mark.parametrize("language,script,expected", [
    ("zh", "simplified", "情绪价值，头发与发展。Hello 123"),
    ("zh", "traditional", "情緒價值，頭髮與發展。Hello 123"),
    ("zh", "original", "情緒價值，頭髮與發展。Hello 123"),
    ("ja", "simplified", "情緒價值，頭髮與發展。Hello 123"),
])
@pytest.mark.parametrize("word_timestamps", [True, False])
def test_preview_and_all_exports_agree(monkeypatch, tmp_path, language, script, expected, word_timestamps):
    text = "情緒價值，頭髮與發展。Hello 123"
    words = [SimpleNamespace(word=text, start=1.25, end=2.5)] if word_timestamps else None
    segment = SimpleNamespace(words=words, start=1.25, end=2.5, text=text)

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, *args, **kwargs):
            return iter([segment]), SimpleNamespace(language=language, language_probability=.99)

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    source = tmp_path / "sample.mp4"
    source.write_bytes(b"x")
    events = []
    options = TranscribeOptions(source, tmp_path, device="cpu", chinese_script=script, word_timestamps=word_timestamps)
    result = transcribe(options, events.append)
    assert result.cues[0].text == expected
    assert result.cues[0].start == 1.25 and result.cues[0].end == 2.5
    assert events[-1]["new_cues"][0].text == expected
    export_result(result, tmp_path, ("srt", "vtt", "txt", "json"))
    for suffix in ("srt", "vtt", "txt"):
        content = (tmp_path / f"sample.{suffix}").read_text(encoding="utf-8-sig")
        assert expected.replace(" ", "") in content.replace("\n", "").replace(" ", "")
    data = json.loads((tmp_path / "sample.json").read_text(encoding="utf-8"))
    assert data["cues"][0]["text"] == expected
    assert data["chinese_script"] == script
    # 人工编辑也必须遵守该次识别的输出设置。
    if language == "zh" and script == "simplified":
        result.cues[0].text = "說話好不好聽"
        export_result(result, tmp_path, ("txt",))
        assert (tmp_path / "sample.txt").read_text(encoding="utf-8-sig").strip() == "说话好不好听"


def test_old_config_defaults_to_simplified_and_choice_persists(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"model":"small"}', encoding="utf-8")
    assert load_config(path)["chinese_script"] == "simplified"
    save_config({"chinese_script": "original"}, path)
    assert load_config(path)["chinese_script"] == "original"
    path.write_text('{"chinese_script":"invalid"}', encoding="utf-8")
    assert load_config(path)["chinese_script"] == "simplified"


def test_traditional_conversion_uses_phrase_context():
    from speech_to_subtitle.chinese import convert_chinese
    assert convert_chinese("头发与发展，后台软件", "traditional") == "頭髮與發展，後臺軟件"
    assert convert_chinese("English 123\n日本語", language="ja") == "English 123\n日本語"
    assert convert_chinese("\n情緒價值\n123", language="yue") == "\n情绪价值\n123"
    with pytest.raises(ValueError):
        convert_chinese("中文", "invalid")
