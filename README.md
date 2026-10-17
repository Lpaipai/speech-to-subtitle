# 听见字幕

“听见字幕”是一个 Windows 本地语音转字幕 APP。选择视频或音频后，使用 faster-whisper 识别人声，并生成 SRT、VTT、TXT 或带完整时间数据的 JSON。

## 为什么选择 faster-whisper

Subtitle Edit 是成熟的完整字幕编辑器，适合复杂人工校对、波形编辑和格式转换；faster-whisper 是语音识别引擎，更适合构建一个流程简单、界面可控的专用 APP。本项目使用 faster-whisper 负责识别，参考 Subtitle Edit 的工作流，没有复制其源码。

## 使用

源码版双击 `启动听见字幕.bat`。免 Python 版打开：

```text
dist\v0.1.1\speech-to-subtitle\听见字幕.exe
```

1. 选择视频或音频。输出目录默认可设为媒体所在目录。
2. 选择语言；不确定时使用“自动识别”。
3. 选择模型和设备，勾选输出格式。
   中文输出默认“简体中文”，也可以选择“繁体中文”或“保持原样”；设置对下次识别生效。
4. 点击“开始识别”。字幕会逐条显示，完成后自动写出文件。
5. 选中字幕行可以修改文字，点击“应用本条”和“保存修改”。

支持 MP4、MKV、MOV、AVI、WebM、M4A、MP3、WAV、FLAC、AAC、OGG、Opus、WMA、MPEG 等常见格式。

## 模型选择

| 模型 | 用途 |
| --- | --- |
| Tiny | 随便携包提供，用于立即试用和快速检查；中文准确率有限 |
| Base | 比 Tiny 稍准，速度快 |
| Small | 默认推荐，日常语音的速度和准确度较平衡 |
| Medium | 中文、口音和噪声环境通常更好，但更慢 |
| Turbo | 适合可用的 NVIDIA GPU |
| Large v3 | 最高精度方向，模型和资源需求最大 |

除 Tiny 外，模型会在首次选择时下载到程序旁的 `models`，以后可以离线使用。首次下载期间进度条为等待状态；停止按钮需要等当前模型下载结束才会生效。

## 当前电脑的运行方式

本机 RTX 3060 Laptop GPU 已被检测到，但当前没有 faster-whisper 需要的 `cublas64_12.dll`，因此“自动”会提示后切换到 CPU。GPU 模式缺少库时不会导致任务丢失。安装 CUDA 12 的 cuBLAS 和 cuDNN 9 后可继续验证 GPU；本版没有修改系统 CUDA、PATH 或 C 盘配置。

建议先用自带 Tiny 确认流程，再下载 Small 做正式转写。Tiny 对本次 30 秒中文样例能够生成有效时间轴，但存在明显错字，不适合最终字幕。

## 输出

- `.srt`：播放器和视频编辑软件常用字幕。
- `.vtt`：网页播放器字幕。
- `.txt`：去掉时间轴的纯文稿。
- `.json`：语言、模型、设备、时间和字幕内容，便于后续处理。

程序在识别全部完成后才写输出；停止或失败不会产生新的不完整字幕。已有同名文件时，界面会先询问是否覆盖。文件采用原子替换，字幕默认为 UTF-8。

“过滤静音”使用 Silero VAD，减少静音段幻觉。“词级时间戳”用于把过长识别段拆成便于阅读的字幕。词汇提示可以填写人名、术语和缩写，帮助模型识别上下文。

## v0.1.1 中文输出优化

使用 OpenCC 纯 Python 转换库统一中文识别结果的简繁字词；实时预览、完成结果、人工编辑后的保存和四种导出格式保持一致。旧配置自动采用简体默认值。只处理识别为中文或粤语的内容，英文、数字及字幕时间不变；日语等其他语言不转换。转换不修复语音识别错词，仍需人工校对。

## 验证

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest -q --basetemp .tmp\pytest
```

已验证基础格式输出、时间码、字幕分段、输入检查、配置和最小窗口布局。另使用真实中文视频的 30 秒音轨执行 Tiny 模型识别，成功生成 17 条 SRT 字幕并验证 GPU 失败后自动切换 CPU。

界面预览见 [`docs/ui-preview.png`](docs/ui-preview.png)，详细结果见 [`docs/验证记录.md`](docs/验证记录.md)。

## 参考

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Subtitle Edit 语音转文字说明](https://github.com/SubtitleEdit/subtitleedit/blob/main/docs/features/speech-to-text.md)
