# 2026/10/01 18:15:08 by liaoweipeng1
from functools import lru_cache

SCRIPTS = {"简体中文": "simplified", "繁体中文": "traditional", "保持原样": "original"}


@lru_cache(maxsize=2)
def _converter(script: str):
    from opencc import OpenCC
    return OpenCC({"simplified": "t2s", "traditional": "s2t"}[script])


def convert_chinese(text: str, script: str = "simplified", language: str = "zh") -> str:
    """只转换中文字词，保留英文、数字、标点和换行。"""
    if script not in SCRIPTS.values():
        raise ValueError(f"不支持的中文输出设置：{script}")
    if language not in {"zh", "yue"} or script == "original" or not text:
        return text
    return _converter(script).convert(text)
