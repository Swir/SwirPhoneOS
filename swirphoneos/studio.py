"""Read-only SwirPhoneStudio developer GUI.

The first GUI deliberately exposes diagnostics only. There are no controls that
can reboot, unlock, erase, flash, format, boot or relock a phone.
"""
from __future__ import annotations

import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser

from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .i18n import system_language, tr
from .profiles import ProfileError, discover_profiles, public_profile_summary
from .reporting import ReportError, write_export


class StudioApp:
    """Small Windows-first/Linux-capable read-only desktop shell."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.language = system_language()
        self.last_kind: str | None = None
        self.last_report: dict[str, object] | None = None
        self.events: queue.Queue[tuple[str, str, dict[str, object] | None]] = queue.Queue()
        self.action_buttons: list[ttk.Button] = []

        root.title(tr("app_title", self.language))
        root.geometry("980x700")
        root.minsize(760, 560)
        root.configure(bg="#07111f")

        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Studio.TFrame", background="#07111f")
        style.configure("Studio.TLabel", background="#07111f", foreground="#d9eaff", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#07111f", foreground="#58b7ff", font=("Segoe UI Semibold", 20))
        style.configure("Warn.TLabel", background="#0d1b2c", foreground="#9ed2ff", font=("Segoe UI Semibold", 10), padding=10)
        style.configure("Studio.TButton", font=("Segoe UI Semibold", 10), padding=(12, 9))
        style.configure("Footer.TLabel", background="#07111f", foreground="#79c7ff", font=("Segoe UI", 9, "underline"))

        outer = ttk.Frame(root, style="Studio.TFrame", padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="SwirPhoneStudio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text=tr("preview", self.language),
            style="Warn.TLabel",
            wraplength=900,
        ).pack(fill="x", pady=(10, 14))

        controls = ttk.Frame(outer, style="Studio.TFrame")
        controls.pack(fill="x")
        self._button(controls, tr("profiles", self.language), self.inspect_profiles).pack(side="left", padx=(0, 8))
        self._button(controls, tr("adb", self.language), self.inspect_adb).pack(side="left", padx=8)
        self._button(controls, tr("fastboot", self.language), self.inspect_fastboot).pack(side="left", padx=8)
        self.export_button = ttk.Button(
            controls,
            text=tr("export", self.language),
            command=self.export_report,
            style="Studio.TButton",
            state="disabled",
        )
        self.export_button.pack(side="right", padx=(8, 0))

        result_frame = ttk.Frame(outer, style="Studio.TFrame")
        result_frame.pack(fill="both", expand=True, pady=(16, 10))
        self.output = tk.Text(
            result_frame,
            wrap="none",
            bg="#050b13",
            fg="#cfe8ff",
            insertbackground="#cfe8ff",
            selectbackground="#1f4d78",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=12,
            font=("Cascadia Mono", 10),
        )
        vertical = ttk.Scrollbar(result_frame, orient="vertical", command=self.output.yview)
        horizontal = ttk.Scrollbar(result_frame, orient="horizontal", command=self.output.xview)
        self.output.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.output.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.status = tk.StringVar(value=tr("ready", self.language))
        ttk.Label(outer, textvariable=self.status, style="Studio.TLabel").pack(fill="x", pady=(0, 8))
        footer = ttk.Label(outer, text=tr("by_swir", self.language), style="Footer.TLabel", cursor="hand2")
        footer.pack(anchor="center")
        footer.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/Swir"))

        self._show({
            "application": "SwirPhoneStudio",
            "mode": "READ_ONLY_DEVELOPER_PREVIEW",
            "language": self.language,
            "flash_allowed": False,
        })
        root.after(100, self._poll_events)

    def _button(self, parent: ttk.Frame, text: str, command: object) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command, style="Studio.TButton")
        self.action_buttons.append(button)
        return button

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self.action_buttons:
            button.configure(state=state)
        if busy or self.last_report is None:
            self.export_button.configure(state="disabled")
        else:
            self.export_button.configure(state="normal")
        self.status.set(tr("working" if busy else "ready", self.language))

    def _show(self, report: dict[str, object]) -> None:
        rendered = json.dumps(report, indent=2, ensure_ascii=True)
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", rendered)
        self.output.configure(state="disabled")

    def _run(self, kind: str, worker: object) -> None:
        self._set_busy(True)

        def task() -> None:
            try:
                report = worker()  # type: ignore[operator]
                if not isinstance(report, dict):
                    raise ValueError("Diagnostic worker returned an invalid report.")
                self.events.put(("ok", kind, report))
            except (DiagnosticError, FastbootDiagnosticError, ProfileError, OSError, ValueError):
                self.events.put(("error", kind, None))

        threading.Thread(target=task, name=f"swir-{kind}-diagnostic", daemon=True).start()

    def _poll_events(self) -> None:
        try:
            while True:
                status, kind, report = self.events.get_nowait()
                self._set_busy(False)
                if status == "ok" and report is not None:
                    self.last_kind = kind
                    self.last_report = report
                    self._show(report)
                    self.status.set(tr("success", self.language))
                    self.export_button.configure(state="normal")
                else:
                    self.status.set(tr("failed", self.language))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    @staticmethod
    def _profile_root() -> Path:
        repository_root = Path(__file__).resolve().parents[1] / "device_packs"
        if repository_root.is_dir():
            return repository_root
        return Path.cwd() / "device_packs"

    def inspect_profiles(self) -> None:
        root = self._profile_root()

        def worker() -> dict[str, object]:
            profiles = discover_profiles(root)
            return {
                "schema_version": 1,
                "profile_count": len(profiles),
                "profiles": [public_profile_summary(profile) for profile in profiles],
                "flash_allowed": False,
            }

        self._run("profiles", worker)

    def inspect_adb(self) -> None:
        path = filedialog.askopenfilename(title=tr("choose_adb", self.language), parent=self.root)
        if path:
            self._run("adb", lambda: ReadOnlyAdb(Path(path)).inspect())

    def inspect_fastboot(self) -> None:
        path = filedialog.askopenfilename(title=tr("choose_fastboot", self.language), parent=self.root)
        if path:
            self._run("fastboot", lambda: ReadOnlyFastboot(Path(path)).inspect())

    def export_report(self) -> None:
        if self.last_report is None or self.last_kind is None:
            self.status.set(tr("nothing_to_export", self.language))
            return
        filename = filedialog.asksaveasfilename(
            title=tr("save_report", self.language),
            parent=self.root,
            defaultextension=".json",
            filetypes=(("JSON", "*.json"),),
        )
        if not filename:
            return
        try:
            write_export(Path(filename), self.last_kind, self.last_report)
        except (ReportError, OSError):
            self.status.set(tr("failed", self.language))
            return
        self.status.set(tr("saved", self.language))


def launch() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError("SwirPhoneStudio GUI is unavailable in this environment.") from exc
    StudioApp(root)
    root.mainloop()
    return 0
