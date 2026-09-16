"""Read-only desktop companion. Run: python -m swirphoneos.studio"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .i18n import CATALOGS, detect_language, translate
from .studio_icon import ICON_PNG
from .studio_state import DiagnosticSession, save_report


class Studio:
    def __init__(self, root: tk.Tk, session: DiagnosticSession | None = None):
        self.root = root
        self.session = session or DiagnosticSession()
        self.language = tk.StringVar(root, value=detect_language())
        self.adb_path = tk.StringVar(root)
        self.status_key = "ready"
        self.started = 0.0
        self.closed = False
        self._labels: list[tuple[tk.Widget, str]] = []
        self._wrapped: list[ttk.Label] = []
        root.title("SwirPhoneOS · Flash Studio")
        root.geometry(f"{min(900, root.winfo_screenwidth() - 60)}x{min(720, root.winfo_screenheight() - 80)}")
        root.minsize(640, 500)
        root.configure(background="#0a1221")
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#0a1221")
        style.configure("TLabel", background="#0a1221", foreground="#e5f0ff", font=("TkDefaultFont", 10))
        style.configure("Title.TLabel", font=("TkDefaultFont", 22, "bold"), foreground="#66dfff")
        style.configure("Notice.TLabel", foreground="#ffd58b", padding=8, background="#182333")
        style.configure("TButton", padding=(12, 6), background="#193650", foreground="#e5f0ff", bordercolor="#234762")
        style.map("TButton", background=[("disabled", "#142537"), ("active", "#225777")],
                  foreground=[("disabled", "#73889c")])
        style.configure("TEntry", fieldbackground="#142537", foreground="#e5f0ff", insertcolor="#e5f0ff")
        style.configure("TCombobox", fieldbackground="#142537", foreground="#e5f0ff", background="#193650")
        style.map("TCombobox", fieldbackground=[("readonly", "#142537")], foreground=[("readonly", "#e5f0ff")])
        style.configure("Horizontal.TProgressbar", background="#40bdf5", troughcolor="#182333")
        self.icon = tk.PhotoImage(master=root, data=ICON_PNG)
        root.iconphoto(True, self.icon)
        outer = ttk.Frame(root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(6, weight=1)
        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, image=self.icon).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ttk.Label(header, text="SwirPhoneOS", style="Title.TLabel").grid(row=0, column=1, rowspan=2, sticky="w")
        self.label(header, "language").grid(row=0, column=2)
        selector = ttk.Combobox(header, textvariable=self.language, values=tuple(CATALOGS), width=5, state="readonly")
        selector.grid(row=1, column=2, sticky="e")
        selector.bind("<<ComboboxSelected>>", lambda _: self.refresh_language())
        self.label(outer, "notice", wrap=True, style="Notice.TLabel").grid(row=1, column=0, sticky="ew", pady=(0, 8))
        fields = ttk.Frame(outer)
        fields.grid(row=2, column=0, sticky="ew")
        fields.columnconfigure(0, weight=1)
        self.label(fields, "adb").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.entry = ttk.Entry(fields, textvariable=self.adb_path)
        self.entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.browse = self.button(fields, "browse", self.choose_adb)
        self.browse.grid(row=1, column=1)
        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, sticky="ew", pady=8)
        self.scan = self.button(actions, "scan", self.start_scan)
        self.scan.pack(side="left", padx=(0, 8))
        self.save = self.button(actions, "save", self.export_report)
        self.save.pack(side="left")
        self.save.state(["disabled"])
        self.status = ttk.Label(outer, text=self.tr("ready"), wraplength=700)
        self._wrapped.append(self.status)
        self.status.grid(row=4, column=0, sticky="ew")
        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=5, column=0, sticky="ew", pady=(6, 8))
        report_frame = ttk.Frame(outer)
        report_frame.grid(row=6, column=0, sticky="nsew")
        report_frame.rowconfigure(1, weight=1)
        report_frame.columnconfigure(0, weight=1)
        self.label(report_frame, "report").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.report = tk.Text(report_frame, wrap="word", state="disabled", height=8,
                              background="#101d30", foreground="#d8edff", insertbackground="white",
                              relief="flat", padx=12, pady=12, font=("TkFixedFont", 10))
        self.report.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(report_frame, orient="vertical", command=self.report.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.report.configure(yscrollcommand=scroll.set)
        self.label(outer, "privacy", wrap=True).grid(row=7, column=0, sticky="ew", pady=8)
        footer = ttk.Frame(outer)
        footer.grid(row=8, column=0, sticky="ew")
        self.button(footer, "github", lambda: webbrowser.open("https://github.com/Swir/SwirPhoneOS")).pack(side="left")
        self.button(footer, "close", self.close).pack(side="right")
        self.show_report(self.tr("empty"))
        root.bind("<Configure>", self.resize)
        root.bind("<Control-o>", lambda _: self.choose_adb())
        root.bind("<Control-s>", lambda _: self.export_report())
        self.after_id = root.after(80, self.poll)

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language.get(), key, **values)

    def label(self, parent: tk.Widget, key: str, wrap: bool = False, **kwargs: object) -> ttk.Label:
        widget = ttk.Label(parent, text=self.tr(key), **kwargs)
        self._labels.append((widget, key))
        if wrap:
            widget.configure(wraplength=700)
            self._wrapped.append(widget)
        return widget

    def button(self, parent: tk.Widget, key: str, command: object) -> ttk.Button:
        widget = ttk.Button(parent, text=self.tr(key), command=command)
        self._labels.append((widget, key))
        return widget

    def resize(self, event: tk.Event) -> None:
        if event.widget is self.root:
            for widget in self._wrapped:
                widget.configure(wraplength=max(240, event.width - 72))

    def refresh_language(self) -> None:
        for widget, key in self._labels:
            widget.configure(text=self.tr(key))
        self.update_status()
        if self.session.report is None:
            self.show_report(self.tr("empty"))

    def update_status(self) -> None:
        self.status.configure(text=self.tr(self.status_key, seconds=int(time.monotonic() - self.started)))

    def show_report(self, text: str) -> None:
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def choose_adb(self) -> None:
        if self.session.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title=self.tr("pick_adb"))
        if path:
            self.adb_path.set(path)

    def start_scan(self) -> None:
        if not self.session.start(Path(self.adb_path.get())):
            return
        self.started = time.monotonic()
        self.status_key = "running"
        for widget in (self.entry, self.browse, self.scan, self.save):
            widget.state(["disabled"])
        self.show_report(self.tr("empty"))
        self.progress.start(15)
        self.update_status()

    def poll(self) -> None:
        if self.closed:
            return
        result = self.session.poll()
        if result is not None:
            self.progress.stop()
            for widget in (self.entry, self.browse, self.scan):
                widget.state(["!disabled"])
            if result.report_json is not None:
                self.status_key = "done"
                self.show_report(result.report_json)
                self.save.state(["!disabled"])
            else:
                self.status_key = result.error_key or "unexpected"
                self.save.state(["disabled"])
        self.update_status()
        self.after_id = self.root.after(80, self.poll)

    def export_report(self) -> None:
        if self.session.busy or self.session.report is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title=self.tr("save"),
                                           defaultextension=".json", initialfile="swirphoneos-report.json",
                                           filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_report(Path(path), self.session.report)
        except (OSError, ValueError):
            messagebox.showerror("SwirPhoneOS", self.tr("save_failed"), parent=self.root)
            return
        self.status_key = "saved"
        self.update_status()

    def close(self) -> None:
        self.closed = True
        self.root.after_cancel(self.after_id)
        self.root.destroy()
        # The daemon finishes a bounded read-only request without accessing Tk.


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only SwirPhoneOS Flash Studio developer UI.")
    parser.add_argument("--smoke-test", action="store_true", help="Open and close the UI without using ADB.")
    args = parser.parse_args()
    try:
        root = tk.Tk()
    except tk.TclError:
        print("A graphical desktop and Tk are required. No device operation was attempted.", file=sys.stderr)
        return 1
    app = Studio(root)
    if args.smoke_test:
        root.after(300, app.close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
