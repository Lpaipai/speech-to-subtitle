from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .chinese import convert_chinese
from .formats import export_result
from .models import TranscribeOptions
from .transcriber import local_model, transcribe


def self_check(target: Path) -> int:
    report = {"version": __version__, "ok": False}
    try:
        if convert_chinese("情緒價值，頭髮與發展。") != "情绪价值，头发与发展。":
            raise RuntimeError("简体转换自检失败")
        if convert_chinese("头发与发展", "traditional") != "頭髮與發展":
            raise RuntimeError("繁体转换自检失败")
        report["chinese_conversion"] = "passed"
        from faster_whisper import WhisperModel
        folder = local_model("tiny")
        if not folder:
            raise RuntimeError("便携包没有找到 Tiny 测试模型")
        model = WhisperModel(str(folder), device="cpu", compute_type="int8")
        report.update({"model": str(folder), "device": "cpu", "ok": True})
    except Exception as exc:
        report["error"] = str(exc)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


def transcription_check(source: Path, target: Path) -> int:
    """Run one real CPU inference for release-package validation."""
    report = {"version": __version__, "source": str(source), "ok": False}
    try:
        output_dir = target.parent / "transcription-check-output"
        options = TranscribeOptions(
            source=source,
            output_dir=output_dir,
            model="tiny",
            language="zh",
            device="cpu",
            vad_filter=True,
            word_timestamps=True,
            formats=("srt", "txt", "json"),
        )
        result = transcribe(options)
        export_result(result, output_dir, options.formats)
        report.update({
            "ok": True,
            "language": result.language,
            "device": result.device,
            "cue_count": len(result.cues),
            "outputs": [str(path) for path in result.outputs],
        })
    except Exception as exc:
        report["error"] = str(exc)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1
