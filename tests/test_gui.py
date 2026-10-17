from speech_to_subtitle.gui import App


def test_gui_opens_at_minimum_size(monkeypatch):
    import speech_to_subtitle.gui as gui
    monkeypatch.setattr(gui, "save_config", lambda *_args, **_kwargs: None)
    app = App()
    try:
        app.geometry("1080x740")
        app.update()
        assert app.start_button.winfo_ismapped()
        assert app.script_var.get() == "简体中文"
        assert app.make_options().chinese_script == "simplified"
        app.script_var.set("保持原样")
        assert app.make_options().chinese_script == "original"
        assert app.progress.winfo_rooty() + app.progress.winfo_height() <= app.winfo_rooty() + app.winfo_height()
    finally:
        app.destroy()
