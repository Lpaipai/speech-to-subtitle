from __future__ import annotations

import gc
import os
from pathlib import Path

from .config import app_root
from .chinese import SCRIPTS, convert_chinese
from .formats import normalize_text
from .models import Cue, TranscribeOptions, TranscribeResult

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus", ".wma", ".mpeg", ".mpg"}


class Cancelled(RuntimeError):
    pass


def validate(options: TranscribeOptions) -> None:
    if options.chinese_script not in SCRIPTS.values():
        raise ValueError("请选择有效的中文输出设置")
    if not options.source.is_file():
        raise ValueError("请选择存在的视频或音频文件")
    if options.source.suffix.lower() not in MEDIA_EXTENSIONS:
        raise ValueError(f"暂不支持 {options.source.suffix or '无扩展名'} 文件")
    if not options.formats:
        raise ValueError("请至少选择一种输出格式")
    options.output_dir.mkdir(parents=True, exist_ok=True)


def media_duration(path: Path) -> float:
    try:
        import av
        with av.open(str(path)) as container:
            if container.duration:
                return float(container.duration / av.time_base)
            values = [float(stream.duration * stream.time_base) for stream in container.streams if stream.duration and stream.time_base]
            return max(values, default=0.0)
    except Exception:
        return 0.0


def model_downloaded(name: str) -> bool:
    root = app_root() / "models"
    return local_model(name) is not None or any(root.glob(f"models--Systran--faster-whisper-{name}/snapshots/*/model.bin")) or any(root.glob(f"models--mobiuslabsgmbh--faster-whisper-{name}/snapshots/*/model.bin")) or any(root.glob(f".cache/hub/models--Systran--faster-whisper-{name}/snapshots/*/model.bin"))


def local_model(name: str) -> Path | None:
    folder = app_root() / "models" / name
    required = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
    return folder if all((folder / filename).is_file() and (folder / filename).stat().st_size > 0 for filename in required) else None


def release_model(model) -> None:
    del model
    gc.collect()
    try:
        import ctranslate2
        ctranslate2.set_random_seed(0)
    except Exception:
        pass


def words_to_cues(segment) -> list[Cue]:
    words = list(segment.words or [])
    if not words:
        text = normalize_text(segment.text)
        return [Cue(float(segment.start), float(segment.end), text)] if text else []
    result: list[Cue] = []
    current = []
    start = None
    for word in words:
        text = word.word or ""
        if start is None:
            start = float(word.start if word.start is not None else segment.start)
        current.append(text)
        joined = normalize_text("".join(current))
        end = float(word.end if word.end is not None else segment.end)
        cjk = sum("\u3400" <= char <= "\u9fff" for char in joined)
        limit = 34 if cjk > len(joined) / 4 else 74
        boundary = text.rstrip().endswith(("。", "！", "？", ".", "!", "?", ";", "；"))
        if len(joined) >= limit or end - start >= 7 or boundary and end - start >= 1.2:
            result.append(Cue(start, max(start + 0.1, end), joined))
            current, start = [], None
    if current and start is not None:
        end = float(words[-1].end if words[-1].end is not None else segment.end)
        result.append(Cue(start, max(start + 0.1, end), normalize_text("".join(current))))
    return result


def _run(options, device, compute_type, callback, should_stop):
    from faster_whisper import WhisperModel
    if should_stop():
        raise Cancelled("用户停止")
    callback({"stage": "model", "message": ("正在加载模型…" if model_downloaded(options.model) else "首次使用正在下载模型，完成后可离线使用…")})
    model_source = str(local_model(options.model) or options.model)
    model = WhisperModel(model_source, device=device, compute_type=compute_type, download_root=str(app_root() / "models"))
    duration = media_duration(options.source)
    callback({"stage": "recognize", "message": f"正在使用 {'GPU' if device == 'cuda' else 'CPU'} 识别…", "current": 0, "total": duration})
    try:
        segments, info = model.transcribe(
            str(options.source), language=options.language, beam_size=5,
            vad_filter=options.vad_filter, vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=options.word_timestamps, condition_on_previous_text=True,
            initial_prompt=options.initial_prompt or None,
        )
        cues: list[Cue] = []
        for segment in segments:
            if should_stop():
                raise Cancelled("用户停止")
            additions = words_to_cues(segment)
            for cue in additions:
                cue.text = convert_chinese(cue.text, options.chinese_script, info.language or "")
            cues.extend(additions)
            callback({"stage": "recognize", "message": additions[-1].text if additions else "", "current": float(segment.end), "total": duration, "cue_count": len(cues), "new_cues": additions})
        if not cues:
            raise RuntimeError("没有识别到语音；请检查文件是否包含清晰人声")
        return TranscribeResult(options.source, info.language or "", float(info.language_probability or 0), duration, options.model, device, cues, chinese_script=options.chinese_script)
    finally:
        release_model(model)


def transcribe(options: TranscribeOptions, callback=lambda _: None, should_stop=lambda: False) -> TranscribeResult:
    validate(options)
    attempts = [("cuda", "int8_float16")] if options.device == "cuda" else [("cpu", "int8")] if options.device == "cpu" else [("cuda", "int8_float16"), ("cpu", "int8")]
    last_error = None
    for index, (device, compute_type) in enumerate(attempts):
        try:
            return _run(options, device, compute_type, callback, should_stop)
        except Cancelled:
            raise
        except Exception as exc:
            last_error = exc
            if index + 1 < len(attempts):
                callback({"stage": "fallback", "message": f"GPU 环境不可用，已自动切换 CPU：{exc}"})
                continue
            raise RuntimeError(f"识别失败：{exc}") from exc
    raise RuntimeError(f"识别失败：{last_error}")
