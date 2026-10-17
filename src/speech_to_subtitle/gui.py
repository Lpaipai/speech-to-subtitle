from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import load_config, prepare_runtime, save_config
from .chinese import SCRIPTS, convert_chinese
from .formats import display_timestamp, export_result
from .models import TranscribeOptions, TranscribeResult
from .transcriber import Cancelled, MEDIA_EXTENSIONS, transcribe

LANGUAGES = {"自动识别": None, "中文": "zh", "英语": "en", "日语": "ja", "韩语": "ko", "法语": "fr", "德语": "de", "西班牙语": "es"}
LANGUAGE_NAMES = {"zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", "fr": "法语", "de": "德语", "es": "西班牙语"}
MODELS = {"Tiny · 测试": "tiny", "Base · 很快": "base", "Small · 推荐": "small", "Medium · 更准确": "medium", "Turbo · GPU 推荐": "turbo", "Large v3 · 最高精度": "large-v3"}
DEVICES = {"自动 · GPU 优先": "auto", "NVIDIA GPU": "cuda", "CPU": "cpu"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("听见字幕 · 本地语音转字幕")
        self.geometry("1240x840")
        self.minsize(1080, 740)
        config = load_config()
        self.source_var = tk.StringVar(value=config["source"])
        self.output_var = tk.StringVar(value=config["output_dir"])
        self.model_var = tk.StringVar(value=next((label for label, value in MODELS.items() if value == config["model"]), "Small · 推荐"))
        self.language_var = tk.StringVar(value=next((label for label, value in LANGUAGES.items() if value == (None if config["language"] == "auto" else config["language"])), "自动识别"))
        self.device_var = tk.StringVar(value=next((label for label, value in DEVICES.items() if value == config["device"]), "自动 · GPU 优先"))
        self.script_var = tk.StringVar(value=next(label for label, value in SCRIPTS.items() if value == config["chinese_script"]))
        self.vad_var = tk.BooleanVar(value=config["vad_filter"])
        self.words_var = tk.BooleanVar(value=config["word_timestamps"])
        self.srt_var = tk.BooleanVar(value=config["srt"])
        self.vtt_var = tk.BooleanVar(value=config["vtt"])
        self.txt_var = tk.BooleanVar(value=config["txt"])
        self.json_var = tk.BooleanVar(value=config["json"])
        self.prompt_var = tk.StringVar(value=config["initial_prompt"])
        self.status_var = tk.StringVar(value="选择视频或音频后开始识别")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="就绪")
        self.summary_var = tk.StringVar(value="还没有识别结果")
        self.current_result: TranscribeResult | None = None
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.drain_events)

    def _build_ui(self):
        from .ui import build_ui
        build_ui(self)

    def choose_source(self):
        path = filedialog.askopenfilename(
            title="选择视频或音频",
            initialdir=str(Path(self.source_var.get()).parent) if self.source_var.get() else r"D:\Codex\sese",
            filetypes=(("视频与音频", "*.mp4 *.mkv *.mov *.avi *.webm *.m4a *.mp3 *.wav *.flac *.aac *.ogg *.opus *.wma *.mpeg *.mpg"), ("所有文件", "*.*")),
        )
        if path:
            self.source_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path(path).parent))
            self.summary_var.set(f"已选择  ·  {Path(path).name}")
            self.save_settings()

    def choose_output(self):
        path = filedialog.askdirectory(initialdir=self.output_var.get() or (str(Path(self.source_var.get()).parent) if self.source_var.get() else r"D:\Codex\sese"))
        if path:
            self.output_var.set(path)
            self.save_settings()

    def selected_formats(self):
        values = (("srt", self.srt_var), ("vtt", self.vtt_var), ("txt", self.txt_var), ("json", self.json_var))
        return tuple(name for name, variable in values if variable.get())

    def make_options(self):
        source = Path(self.source_var.get().strip())
        output = Path(self.output_var.get().strip()) if self.output_var.get().strip() else source.parent
        return TranscribeOptions(
            source=source, output_dir=output, model=MODELS[self.model_var.get()],
            language=LANGUAGES[self.language_var.get()], device=DEVICES[self.device_var.get()],
            initial_prompt=self.prompt_var.get().strip(), vad_filter=self.vad_var.get(),
            word_timestamps=self.words_var.get(), formats=self.selected_formats(),
            chinese_script=SCRIPTS[self.script_var.get()],
        )

    def start(self):
        if self.is_running():
            return
        options = self.make_options()
        if not options.source.is_file():
            messagebox.showwarning("没有媒体文件", "请先选择存在的视频或音频文件。")
            return
        if options.source.suffix.lower() not in MEDIA_EXTENSIONS:
            messagebox.showwarning("文件不支持", f"暂不支持 {options.source.suffix or '无扩展名'} 文件。")
            return
        if not options.formats:
            messagebox.showwarning("没有输出格式", "请至少选择 SRT、VTT、TXT 或 JSON 中的一种。")
            return
        existing = [options.output_dir / f"{options.source.stem}.{suffix}" for suffix in options.formats]
        existing = [path for path in existing if path.exists()]
        if existing and not messagebox.askyesno("覆盖已有字幕", "以下输出已存在：\n\n" + "\n".join(path.name for path in existing) + "\n\n是否覆盖？"):
            return
        self.current_result = None
        self.table.delete(*self.table.get_children())
        self.preview.delete("1.0", tk.END)
        self.stop_event.clear()
        self.progress_var.set(0)
        self.progress_text_var.set("准备中")
        self.status_var.set("正在准备识别…")
        self.summary_var.set("模型加载后将开始显示识别结果")
        self.set_running(True)
        self.save_settings()
        self.worker = threading.Thread(target=self.run_worker, args=(options,), daemon=True)
        self.worker.start()

    def run_worker(self, options):
        try:
            result = transcribe(options, lambda event: self.events.put(("progress", event)), self.stop_event.is_set)
            if self.stop_event.is_set():
                raise Cancelled("用户停止")
            export_result(result, options.output_dir, options.formats)
            self.events.put(("done", result))
        except Cancelled:
            self.events.put(("stopped", None))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def stop(self):
        self.stop_event.set()
        self.status_var.set("正在安全停止；当前识别片段结束后退出…")
        self.stop_button.configure(state="disabled")

    def drain_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self.handle_progress(payload)
                elif kind == "done":
                    self.show_result(payload)
                elif kind == "stopped":
                    self.status_var.set("已停止，没有写入不完整字幕")
                    self.progress_text_var.set("已停止")
                    self.set_running(False)
                elif kind == "error":
                    self.status_var.set("识别失败")
                    self.progress_text_var.set("失败")
                    self.set_running(False)
                    messagebox.showerror("识别失败", str(payload))
        except queue.Empty:
            pass
        self.after(100, self.drain_events)

    def handle_progress(self, event):
        message = str(event.get("message", ""))
        stage = event.get("stage")
        if stage in {"model", "fallback"}:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
            self.progress_text_var.set("下载/加载模型" if stage == "model" else "切换 CPU")
        elif stage == "recognize":
            self.progress.stop()
            total = float(event.get("total") or 0)
            current = float(event.get("current") or 0)
            if total:
                self.progress.configure(mode="determinate")
                percent = min(100, current / total * 100)
                self.progress_var.set(percent)
                self.progress_text_var.set(f"{percent:.0f}%  ·  {display_timestamp(current)} / {display_timestamp(total)}")
            else:
                self.progress.configure(mode="indeterminate")
                self.progress.start(12)
                self.progress_text_var.set("识别中")
            for cue in event.get("new_cues", []):
                index = len(self.table.get_children()) + 1
                self.table.insert("", "end", iid=f"live-{index}", values=(index, display_timestamp(cue.start), display_timestamp(cue.end), cue.text))
                self.table.see(f"live-{index}")
            count = event.get("cue_count")
            if count:
                self.summary_var.set(f"已经识别 {count} 条字幕")
        if message:
            self.status_var.set(message[:180])

    def show_result(self, result):
        self.current_result = result
        self.table.delete(*self.table.get_children())
        for index, cue in enumerate(result.cues, 1):
            self.table.insert("", "end", iid=str(index - 1), values=(index, display_timestamp(cue.start), display_timestamp(cue.end), cue.text))
        language = LANGUAGE_NAMES.get(result.language, result.language or "未知")
        self.summary_var.set(f"{len(result.cues)} 条字幕  ·  {language} {result.language_probability:.0%}  ·  {result.model}  ·  {result.device.upper()}")
        self.status_var.set("识别完成：" + "、".join(path.name for path in result.outputs))
        self.progress_var.set(100)
        self.progress_text_var.set("100%")
        self.set_running(False)
        if result.cues:
            self.table.selection_set("0")
            self.on_select()

    def on_select(self, _event=None):
        if not self.current_result or not self.table.selection():
            return
        index = int(self.table.selection()[0])
        cue = self.current_result.cues[index]
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", cue.text)

    def apply_edit(self):
        if not self.current_result or not self.table.selection():
            return
        index = int(self.table.selection()[0])
        text = self.preview.get("1.0", tk.END).strip()
        text = convert_chinese(text, self.current_result.chinese_script, self.current_result.language)
        if not text:
            messagebox.showwarning("字幕为空", "字幕文字不能为空。")
            return
        self.current_result.cues[index].text = text
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", text)
        values = list(self.table.item(str(index), "values"))
        values[3] = text
        self.table.item(str(index), values=values)
        self.status_var.set("修改尚未写入文件，请点击“保存修改”")

    def save_edits(self):
        if not self.current_result:
            return
        self.apply_edit()
        formats = self.selected_formats()
        if not formats:
            messagebox.showwarning("没有输出格式", "请至少选择一种输出格式。")
            return
        output = Path(self.output_var.get()) if self.output_var.get() else self.current_result.source.parent
        export_result(self.current_result, output, formats)
        self.status_var.set("修改已保存：" + "、".join(path.name for path in self.current_result.outputs))

    def open_output(self):
        path = Path(self.output_var.get()) if self.output_var.get() else Path(self.source_var.get()).parent
        if not str(path):
            return
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer.exe", str(path)])

    def set_running(self, running):
        state = "disabled" if running else "normal"
        self.start_button.configure(state=state)
        self.source_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")
        self.save_button.configure(state="disabled" if running or not self.current_result else "normal")
        if not running:
            self.progress.stop()
            self.progress.configure(mode="determinate")

    def is_running(self):
        return bool(self.worker and self.worker.is_alive())

    def save_settings(self):
        save_config({
            "source": self.source_var.get(), "output_dir": self.output_var.get(),
            "model": MODELS[self.model_var.get()], "language": LANGUAGES[self.language_var.get()] or "auto",
            "device": DEVICES[self.device_var.get()], "vad_filter": self.vad_var.get(),
            "word_timestamps": self.words_var.get(), "srt": self.srt_var.get(), "vtt": self.vtt_var.get(),
            "txt": self.txt_var.get(), "json": self.json_var.get(), "initial_prompt": self.prompt_var.get(),
            "chinese_script": SCRIPTS[self.script_var.get()],
        })

    def on_close(self):
        self.save_settings()
        if self.is_running():
            self.stop_event.set()
            self.status_var.set("正在停止并关闭…")
            self.after(200, self.on_close)
            return
        self.destroy()


def main():
    prepare_runtime()
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--self-check":
        from .diagnostics import self_check
        raise SystemExit(self_check(Path(sys.argv[2])))
    if len(sys.argv) == 4 and sys.argv[1] == "--transcribe-check":
        from .diagnostics import transcription_check
        raise SystemExit(transcription_check(Path(sys.argv[2]), Path(sys.argv[3])))
    App().mainloop()
