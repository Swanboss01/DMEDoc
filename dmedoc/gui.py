"""Interface graphique tkinter de DMEDoc."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .report import report_bin, report_check, report_diff


def list_ports() -> list[str]:
    try:
        from serial.tools import list_ports as lp

        return [p.device for p in lp.comports()]
    except Exception:
        return []


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"DMEDoc {__version__} — PREVIEW (lecture seule)")
        self.geometry("760x520")
        self.minsize(600, 400)

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Port K-line :").pack(side="left")
        self.port = ttk.Combobox(top, width=10, values=list_ports())
        self.port.pack(side="left", padx=4)
        if self.port["values"]:
            self.port.current(0)
        ttk.Button(top, text="Actualiser", command=self.refresh_ports).pack(side="left")
        self.btn_check = ttk.Button(top, text="Diagnostiquer le calculateur", command=self.on_check)
        self.btn_check.pack(side="left", padx=12)

        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill="x")
        ttk.Button(mid, text="Analyser un .bin…", command=self.on_bin).pack(side="left")
        ttk.Button(mid, text="Comparer deux .bin…", command=self.on_diff).pack(side="left", padx=6)
        ttk.Button(mid, text="Copier le rapport", command=self.on_copy).pack(side="right")

        self.out = tk.Text(self, wrap="word", font=("Consolas", 10))
        self.out.pack(fill="both", expand=True, padx=8, pady=8)
        self.show(
            "Bienvenue. Version preview, jamais testée sur un vrai calculateur.\n"
            "Rien n'est écrit dans le calculateur : lecture seule.\n\n"
            "1) Branche le câble K-line, alimente le calculateur (12 V + contact), choisis le port,\n"
            "   puis « Diagnostiquer le calculateur ».\n"
            "2) Ou analyse un dump .bin fait avec MS4x Flasher."
        )

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

    def on_check(self) -> None:
        port = self.port.get().strip()
        if not port:
            messagebox.showwarning("DMEDoc", "Choisis un port série (aucun détecté ? Actualiser).")
            return
        self.btn_check.state(["disabled"])
        self.show(f"Interrogation du calculateur sur {port}…")

        def work() -> None:
            try:
                text, _ = report_check(port)
            except Exception as e:  # ne jamais laisser le thread mourir en silence
                text = f"[ERREUR] Erreur inattendue : {e!r}"
            self.after(0, lambda: (self.show(text), self.btn_check.state(["!disabled"])))

        threading.Thread(target=work, daemon=True).start()

    def on_bin(self) -> None:
        path = filedialog.askopenfilename(title="Dump .bin", filetypes=[("Dump", "*.bin"), ("Tous", "*.*")])
        if not path:
            return
        try:
            self.show(report_bin(path))
        except OSError as e:
            self.show(f"[ERREUR] Lecture impossible : {e}")

    def on_diff(self) -> None:
        a = filedialog.askopenfilename(title="Premier .bin", filetypes=[("Dump", "*.bin"), ("Tous", "*.*")])
        if not a:
            return
        b = filedialog.askopenfilename(title="Second .bin", filetypes=[("Dump", "*.bin"), ("Tous", "*.*")])
        if not b:
            return
        try:
            text, _ = report_diff(a, b)
            self.show(f"A : {a}\nB : {b}\n\n{text}")
        except OSError as e:
            self.show(f"[ERREUR] Lecture impossible : {e}")


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
