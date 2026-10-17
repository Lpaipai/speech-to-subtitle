from types import SimpleNamespace

import pytest

from speech_to_subtitle.models import TranscribeOptions
from speech_to_subtitle.transcriber import validate, words_to_cues


def test_validation_rejects_missing_source_and_empty_formats(tmp_path):
    with pytest.raises(ValueError, match="存在"):
        validate(TranscribeOptions(tmp_path / "missing.mp4", tmp_path))
    source = tmp_path / "a.mp4"
    source.write_bytes(b"x")
    with pytest.raises(ValueError, match="输出格式"):
        validate(TranscribeOptions(source, tmp_path, formats=()))


def test_words_split_at_sentence_boundaries():
    words = [
        SimpleNamespace(word="你好", start=0.0, end=.5),
        SimpleNamespace(word="世界。", start=.5, end=1.5),
        SimpleNamespace(word="第二句", start=1.5, end=2.2),
    ]
    segment = SimpleNamespace(words=words, start=0.0, end=2.2, text="你好世界。第二句")
    cues = words_to_cues(segment)
    assert [cue.text for cue in cues] == ["你好世界。", "第二句"]
    assert cues[0].end <= cues[1].start


def test_segment_without_words_is_preserved():
    segment = SimpleNamespace(words=None, start=1.0, end=2.0, text="  hello  world ")
    assert words_to_cues(segment)[0].text == "hello world"
