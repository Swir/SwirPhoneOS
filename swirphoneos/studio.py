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
from .studio_evidence import (
    StudioEvidenceError,
    load_public_device_physical_validation_summary,
    load_public_swirroot_readiness_summary,
)
from .studio_icon import ICON_PNG
from .studio_state import DiagnosticSession, UnifiedDiagnosticSession, save_report


class Studio:
    def __init__(
        self,
        root: tk.Tk,
        session: DiagnosticSession | UnifiedDiagnosticSession | None = None,
    ):
        self.root = root
        self.session = session or UnifiedDiagnosticSession()
        self.language = tk.StringVar(root, value=detect_language())
        self.transport = tk.StringVar(root, value="ADB")
        self.tool_path = tk.StringVar(root)
        # Compatibility alias for existing embeddings/tests from the ADB-only slice.
        self.adb_path = self.tool_path
        self.status_key = "ready"
        self.started = 0.0
        self.closed = False
        self.readiness_summary: dict[str, object] | None = None
        self.device_validation_summary: dict[str, object] | None = None
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
        language_selector = ttk.Combobox(
            header, textvariable=self.language, values=tuple(CATALOGS), width=5, state="readonly"
        )
        language_selector.grid(row=1, column=2, sticky="e")
        language_selector.bind("<<ComboboxSelected>>", lambda _: self.refresh_language())
        self.label(outer, "notice", wrap=True, style="Notice.TLabel").grid(row=1, column=0, sticky="ew", pady=(0, 8))

        fields = ttk.Frame(outer)
        fields.grid(row=2, column=0, sticky="ew")
        fields.columnconfigure(0, weight=1)
        field_header = ttk.Frame(fields)
        field_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        self.transport_selector = ttk.Combobox(
            field_header, textvariable=self.transport, values=("ADB", "Fastboot"), width=10, state="readonly"
        )
        self.transport_selector.pack(side="left", padx=(0, 12))
        self.transport_selector.bind("<<ComboboxSelected>>", lambda _: self.refresh_transport())

        self.entry = ttk.Entry(fields, textvariable=self.tool_path)
        self.entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.browse = self.button(fields, "browse", self.choose_tool)
        self.browse.grid(row=1, column=1)

        # Two action rows prevent translated review labels from overlapping on
        # narrow Windows displays while keeping the scan/save controls primary.
        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, sticky="ew", pady=6)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.scan = self.button(actions, "scan", self.start_scan)
        self.scan.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        self.save = self.button(actions, "save", self.export_report)
        self.save.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 4))
        self.save.state(["disabled"])
        self.readiness = self.button(actions, "review_readiness", self.open_root_readiness)
        self.readiness.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.device_validation = self.button(actions, "review_device_validation", self.open_device_validation)
        self.device_validation.grid(row=1, column=1, sticky="ew", padx=(4, 0))

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
        root.bind("<Control-o>", lambda _: self.choose_tool())
        root.bind("<Control-s>", lambda _: self.export_report())
        root.bind("<Control-r>", lambda _: self.open_root_readiness())
        root.bind("<Control-d>", lambda _: self.open_device_validation())
        self.after_id = root.after(80, self.poll)

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language.get(), key, **values)

    def transport_code(self) -> str:
        return "fastboot" if self.transport.get() == "Fastboot" else "adb"

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
        if self.readiness_summary is not None:
            self.show_report(self.render_readiness(self.readiness_summary))
        elif self.device_validation_summary is not None:
            self.show_report(self.render_device_validation(self.device_validation_summary))
        elif self.session.report is None:
            self.show_report(self.tr("empty"))

    def refresh_transport(self) -> None:
        if self.session.busy:
            return
        self.tool_path.set("")
        self.status_key = "ready"
        self.save.state(["disabled"])
        self.session.report = None
        self.readiness_summary = None
        self.device_validation_summary = None
        self.show_report(self.tr("empty"))
        self.update_status()

    def update_status(self) -> None:
        self.status.configure(text=self.tr(self.status_key, seconds=int(time.monotonic() - self.started)))

    def show_report(self, text: str) -> None:
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def choose_tool(self) -> None:
        if self.session.busy:
            return
        path = filedialog.askopenfilename(parent=self.root, title=self.tr("browse"))
        if path:
            self.tool_path.set(path)

    def choose_adb(self) -> None:
        """Compatibility alias for the previous ADB-only GUI API."""
        self.choose_tool()

    def render_readiness(self, summary: dict[str, object]) -> str:
        missing = summary["missing_requirements"]
        missing_text = (
            ", ".join(self.tr(f"readiness_gate_{item}") for item in missing)
            if missing
            else self.tr("none")
        )
        action = self.tr(f"readiness_action_{summary['action']}")
        yes = self.tr("yes")
        no = self.tr("no")
        return self.tr(
            "readiness_summary",
            action=action,
            profile=summary["profile_id"],
            build=summary["exact_build"],
            transaction=summary["transaction_id"],
            missing=missing_text,
            backend=yes if summary["policy_backend_available"] is True else no,
            transition=yes if summary["transition_ready"] is True else no,
            writes=yes if summary["device_write_allowed"] is True else no,
        )

    def render_device_validation(self, summary: dict[str, object]) -> str:
        failures = summary["known_capability_failures"]
        failures_text = (
            ", ".join(self.tr(f"device_capability_{item}") for item in failures)
            if failures
            else self.tr("none")
        )
        missing = summary["missing_requirements"]
        # Missing requirement values are stable evidence-schema identifiers.
        # The explanatory UI copy remains fully localized while identifiers are
        # intentionally preserved verbatim for operator/debug correspondence.
        missing_text = ", ".join(str(item) for item in missing) if missing else self.tr("none")
        yes = self.tr("yes")
        no = self.tr("no")
        return self.tr(
            "device_validation_summary",
            session=summary["validation_session_id"],
            profile=summary["profile_id"],
            build=summary["target_build"],
            candidate=yes if summary["support_candidate_review_ready"] is True else no,
            failures=failures_text,
            missing=missing_text,
            support=yes if summary["support_claim_allowed"] is True else no,
            writes=yes if summary["device_write_allowed"] is True else no,
        )

    def open_root_readiness(self) -> None:
        if self.session.busy:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title=self.tr("review_readiness"),
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            # Do not resolve here: resolving could turn a selected symlink into
            # its regular target and bypass the evidence loader's symlink gate.
            summary = load_public_swirroot_readiness_summary(Path(path))
        except (OSError, StudioEvidenceError, ValueError):
            messagebox.showerror("SwirPhoneOS", self.tr("readiness_failed"), parent=self.root)
            return
        self.readiness_summary = summary
        self.device_validation_summary = None
        self.status_key = "readiness_loaded"
        self.save.state(["disabled"])
        self.show_report(self.render_readiness(summary))
        self.update_status()

    def open_device_validation(self) -> None:
        if self.session.busy:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title=self.tr("review_device_validation"),
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            # Preserve the selected path so symlink rejection remains effective.
            summary = load_public_device_physical_validation_summary(Path(path))
        except (OSError, StudioEvidenceError, ValueError):
            messagebox.showerror("SwirPhoneOS", self.tr("device_validation_failed"), parent=self.root)
            return
        self.device_validation_summary = summary
        self.readiness_summary = None
        self.status_key = "device_validation_loaded"
        self.save.state(["disabled"])
        self.show_report(self.render_device_validation(summary))
        self.update_status()

    def start_scan(self) -> None:
        executable = Path(self.tool_path.get())
        if isinstance(self.session, UnifiedDiagnosticSession):
            started = self.session.start(executable, self.transport_code())
        else:
            started = self.session.start(executable)
        if not started:
            return
        self.started = time.monotonic()
        self.status_key = "running"
        self.readiness_summary = None
        self.device_validation_summary = None
        for widget in (
            self.entry, self.browse, self.scan, self.save, self.readiness,
            self.device_validation, self.transport_selector,
        ):
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
            for widget in (
                self.entry, self.browse, self.scan, self.readiness,
                self.device_validation, self.transport_selector,
            ):
                widget.state(["!disabled"])
            if result.report_json is not None:
                self.status_key = "done"
                self.readiness_summary = None
                self.device_validation_summary = None
                self.show_report(result.report_json)
                self.save.state(["!disabled"])
            else:
                self.status_key = result.error_key or "unexpected"
                self.save.state(["disabled"])
        self.update_status()
        self.after_id = self.root.after(80, self.poll)

    def export_report(self) -> None:
        if (
            self.session.busy
            or self.session.report is None
            or self.readiness_summary is not None
            or self.device_validation_summary is not None
        ):
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
    parser.add_argument("--smoke-test", action="store_true", help="Open and close the UI without using Android SDK tools.")
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
