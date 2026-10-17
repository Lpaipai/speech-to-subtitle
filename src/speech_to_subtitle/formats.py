from __future__ import annotations

import json
import re
import textwrap
from dataclasses import asdict
from pathlib import Path

from .models import Cue, TranscribeResult
from .chinese import convert_chinese


def timestamp(seconds: float, separator: str = ",") -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{milliseconds:03d}"


def display_timestamp(seconds: float) -> str:
    return timestamp(seconds, ".")[:-4]


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+([，。！？、；：,.!?;:])", r"\1", value.strip())
    value = re.sub(r"\s+", " ", value)
    return value


def wrap_subtitle(text: str) -> str:
    text = normalize_text(text)
    if not text:
        return ""
    cjk = sum("\u3400" <= char <= "\u9fff" for char in text)
    width = 22 if cjk > len(text) / 4 else 42
    if len(text) <= width:
        return text
    if cjk:
        middle = min(range(max(1, len(text) // 2 - 8), min(len(text), len(text) // 2 + 9)), key=lambda i: (text[i] not in "，。！？、；： ", abs(i - len(text) / 2)))
        return text[: middle + 1].strip() + "\n" + text[middle + 1 :].strip()
    return "\n".join(textwrap.wrap(text, width=width, max_lines=2, placeholder="…"))


def safe_stem(path: Path) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", path.stem).strip(". ") or "字幕"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8-sig" if path.suffix == ".txt" else "utf-8")
    temp.replace(path)


def export_result(result: TranscribeResult, output_dir: Path, formats: tuple[str, ...]) -> list[Path]:
    for cue in result.cues:
        cue.text = convert_chinese(cue.text, result.chinese_script, result.language)
    stem = safe_stem(result.source)
    outputs: list[Path] = []
    if "srt" in formats:
        path = output_dir / f"{stem}.srt"
        blocks = [f"{index}\n{timestamp(cue.start)} --> {timestamp(cue.end)}\n{wrap_subtitle(cue.text)}" for index, cue in enumerate(result.cues, 1)]
        atomic_write(path, "\n\n".join(blocks) + "\n")
        outputs.append(path)
    if "vtt" in formats:
        path = output_dir / f"{stem}.vtt"
        blocks = [f"{timestamp(cue.start, '.')} --> {timestamp(cue.end, '.')}\n{wrap_subtitle(cue.text)}" for cue in result.cues]
        atomic_write(path, "WEBVTT\n\n" + "\n\n".join(blocks) + "\n")
        outputs.append(path)
    if "txt" in formats:
        path = output_dir / f"{stem}.txt"
        atomic_write(path, "\n".join(cue.text for cue in result.cues) + "\n")
        outputs.append(path)
    if "json" in formats:
        path = output_dir / f"{stem}.json"
        payload = {
            "source": str(result.source), "language": result.language,
            "language_probability": result.language_probability,
            "duration": result.duration, "model": result.model, "device": result.device,
            "chinese_script": result.chinese_script,
            "cues": [asdict(cue) for cue in result.cues],
        }
        atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        outputs.append(path)
    result.outputs = outputs
    return outputs
