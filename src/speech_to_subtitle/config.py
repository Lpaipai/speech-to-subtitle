from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

DEFAULTS = {
    "source": "",
    "output_dir": "",
    "model": "small",
    "language": "auto",
    "chinese_script": "simplified",
    "device": "auto",
    "vad_filter": True,
    "word_timestamps": True,
    "srt": True,
    "vtt": False,
    "txt": True,
    "json": False,
    "initial_prompt": "",
}


def app_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]


def prepare_runtime() -> None:
    temporary = app_root() / ".tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
    os.environ["HF_HOME"] = str(app_root() / "models" / ".cache")
    os.environ["HF_HUB_CACHE"] = str(app_root() / "models" / ".cache" / "hub")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    tempfile.tempdir = str(temporary)


def config_path() -> Path:
    return app_root() / ".speech-to-subtitle-config.json"


def load_config(path: Path | None = None) -> dict:
    data = dict(DEFAULTS)
    try:
        loaded = json.loads((path or config_path()).read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data.update({key: loaded[key] for key in data if key in loaded})
    except (OSError, ValueError):
        pass
    if data["model"] not in {"tiny", "base", "small", "medium", "turbo", "large-v3"}:
        data["model"] = "small"
    if data["device"] not in {"auto", "cuda", "cpu"}:
        data["device"] = "auto"
    if data["chinese_script"] not in {"simplified", "traditional", "original"}:
        data["chinese_script"] = "simplified"
    return data


def save_config(values: dict, path: Path | None = None) -> None:
    target = path or config_path()
    data = dict(DEFAULTS)
    data.update({key: values[key] for key in data if key in values})
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(target)
