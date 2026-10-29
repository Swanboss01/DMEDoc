"""DMEDoc tkinter GUI."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .i18n import LANGS, load_saved_lang, save_lang, set_lang, t
from .report import report_bin, report_check, report_diff


def list_ports() -> list[str]:
    try:
        from serial.tools import list_ports as lp

        return [p.device for p in lp.comports()]
    except Exception:
        return []


def _icon_path() -> str:
    """assets/dmedoc.png, from the PyInstaller bundle or the repo."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "dmedoc.png")


def set_window_icon(win: tk.Tk) -> None:
    try:
        win._icon = tk.PhotoImage(file=_icon_path())  # keep a reference
        win.iconphoto(True, win._icon)
    except (tk.TclError, OSError):
        pass  # missing icon is cosmetic only


def choose_language() -> str:
    """Small modal window asking for the language. Closing it keeps English."""
    root = tk.Tk()
    root.title("DMEDoc")
    set_window_icon(root)
    root.resizable(False, False)
    chosen = {"lang": "en"}

    ttk.Label(root, text="Choose your language / Choisissez votre langue", padding=14).pack()
    row = ttk.Frame(root, padding=(14, 0, 14, 14))
    row.pack()

    def pick(code: str) -> None:
        chosen["lang"] = code
        root.destroy()

    for code, label in LANGS.items():
        ttk.Button(row, text=label, width=14, command=lambda c=code: pick(c)).pack(side="left", padx=6)

    root.mainloop()
    return chosen["lang"]


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.restart = False
        set_window_icon(self)
        self.title(t("title", ver=__version__))
        self.geometry("760x520")
        self.minsize(600, 400)

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text=t("port_label")).pack(side="left")
        self.port = ttk.Combobox(top, width=10, values=list_ports())
        self.port.pack(side="left", padx=4)
        if self.port["values"]:
            self.port.current(0)
        ttk.Button(top, text=t("refresh"), command=self.refresh_ports).pack(side="left")
        self.btn_check = ttk.Button(top, text=t("btn_check"), command=self.on_check)
        self.btn_check.pack(side="left", padx=12)

        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill="x")
        ttk.Button(mid, text=t("btn_bin"), command=self.on_bin).pack(side="left")
        ttk.Button(mid, text=t("btn_diff"), command=self.on_diff).pack(side="left", padx=6)
        ttk.Button(mid, text=t("btn_copy"), command=self.on_copy).pack(side="right")
        ttk.Button(mid, text=t("btn_lang"), command=self.on_lang).pack(side="right", padx=6)
        ttk.Button(mid, text=t("btn_sim"), command=self.on_sim).pack(side="left", padx=6)

        self.out = tk.Text(self, wrap="word", font=("Consolas", 10))
        self.out.pack(fill="both", expand=True, padx=8, pady=8)
        self.show(t("welcome"))

    def refresh_ports(self) -> None:
        self.port["values"] = list_ports()
        if self.port["values"]:
            self.port.current(0)

    def show(self, text: str) -> None:
        self.out.delete("1.0", "end")
        self.out.insert("end", text)

    def on_copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.out.get("1.0", "end").strip())

    def on_sim(self) -> None:
        """Panda3D needs its own main loop: run the simulator as a separate process."""
        import importlib.util
        import subprocess

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--sim"]
        elif importlib.util.find_spec("panda3d") is None or importlib.util.find_spec("gltf") is None:
            messagebox.showwarning("DMEDoc", t("sim_unavailable"))
            return
        else:
            cmd = [sys.executable, "-m", "dmedoc", "sim"]
        try:
            subprocess.Popen(cmd)
        except OSError as e:
            self.show(f"{t('lvl_error')} {e}")

    def on_lang(self) -> None:
        self.restart = True
        self.destroy()

    def on_check(self) -> None:
        port = self.port.get().strip()
        if not port:
            messagebox.showwarning("DMEDoc", t("no_port"))
            return
        self.btn_check.state(["disabled"])
        self.show(t("querying", port=port))

        def work() -> None:
            try:
                text, _ = report_check(port)
            except Exception as e:  # never let the worker die silently
                text = f"{t('lvl_error')} {t('unexpected', err=repr(e))}"
            self.after(0, lambda: (self.show(text), self.btn_check.state(["!disabled"])))

        threading.Thread(target=work, daemon=True).start()

    def on_bin(self) -> None:
        path = filedialog.askopenfilename(title=t("dlg_bin"), filetypes=[("Dump", "*.bin"), ("All", "*.*")])
        if not path:
            return
        try:
            self.show(report_bin(path))
        except OSError as e:
            self.show(f"{t('lvl_error')} {t('read_error', err=e)}")

    def on_diff(self) -> None:
        a = filedialog.askopenfilename(title=t("dlg_first"), filetypes=[("Dump", "*.bin"), ("All", "*.*")])
        if not a:
            return
        b = filedialog.askopenfilename(title=t("dlg_second"), filetypes=[("Dump", "*.bin"), ("All", "*.*")])
        if not b:
            return
        try:
            text, _ = report_diff(a, b)
            self.show(f"A: {a}\nB: {b}\n\n{text}")
        except OSError as e:
            self.show(f"{t('lvl_error')} {t('read_error', err=e)}")


def main() -> None:
    lang = load_saved_lang()
    if lang is None:  # first launch: ask
        lang = choose_language()
        save_lang(lang)
    set_lang(lang)

    while True:
        app = App()
        app.mainloop()
        if not app.restart:
            break
        lang = choose_language()
        save_lang(lang)
        set_lang(lang)


if __name__ == "__main__":
    main()
