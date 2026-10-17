from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TranscribeOptions:
    source: Path
    output_dir: Path
    model: str = "small"
    language: str | None = None
    device: str = "auto"
    initial_prompt: str = ""
    vad_filter: bool = True
    word_timestamps: bool = True
    formats: tuple[str, ...] = ("srt", "txt")
    chinese_script: str = "simplified"


@dataclass
class Cue:
    start: float
    end: float
    text: str


@dataclass
class TranscribeResult:
    source: Path
    language: str = ""
    language_probability: float = 0.0
    duration: float = 0.0
    model: str = ""
    device: str = ""
    cues: list[Cue] = field(default_factory=list)
    outputs: list[Path] = field(default_factory=list)
    chinese_script: str = "simplified"
