import json

from speech_to_subtitle.formats import export_result, normalize_text, timestamp, wrap_subtitle
from speech_to_subtitle.models import Cue, TranscribeResult


def test_timestamp_handles_rounding_and_hours():
    assert timestamp(3661.9996) == "01:01:02,000"
    assert timestamp(-1) == "00:00:00,000"


def test_text_cleanup_and_wrap():
    assert normalize_text(" hello  ,  world ") == "hello, world"
    wrapped = wrap_subtitle("这是一个需要分成两行显示的中文长句子，因为单行字幕太长时会影响观看体验")
    assert wrapped.count("\n") == 1


def test_export_all_formats(tmp_path):
    source = tmp_path / "my video.mp4"
    source.write_bytes(b"x")
    result = TranscribeResult(source, "zh", .98, 2.0, "tiny", "cpu", [Cue(0, 1.25, "第一句。"), Cue(1.25, 2, "Second line.")])
    paths = export_result(result, tmp_path / "out", ("srt", "vtt", "txt", "json"))
    assert {path.suffix for path in paths} == {".srt", ".vtt", ".txt", ".json"}
    assert "00:00:00,000 --> 00:00:01,250" in (tmp_path / "out/my video.srt").read_text(encoding="utf-8")
    assert (tmp_path / "out/my video.vtt").read_text(encoding="utf-8").startswith("WEBVTT")
    assert json.loads((tmp_path / "out/my video.json").read_text(encoding="utf-8"))["language"] == "zh"
