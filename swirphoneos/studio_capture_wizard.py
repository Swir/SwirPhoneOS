"""Owner-visible read-only physical-device capture wizard for SwirPhoneStudio.

The controller binds the existing create-only capture-session evidence flow to a
small desktop workflow. It intentionally exposes no automated device mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .device_capture_session import (
    DeviceCaptureSessionError,
    create_capture_session,
    finalize_capture_session,
    public_capture_status,
    record_transport_report,
    verify_capture_session,
)
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .i18n import translate
from .identity import IdentityAssessmentError, build_unified_report
from .profiles import ProfileError, discover_profiles


_CAPTURE_ERRORS = (
    DeviceCaptureSessionError,
    DiagnosticError,
    FastbootDiagnosticError,
    IdentityAssessmentError,
    ProfileError,
    OSError,
    ValueError,
)


def bundled_profiles_root() -> Path:
    """Return the reviewed device-profile registry for source or frozen builds."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if isinstance(frozen_root, str) and frozen_root:
        return Path(frozen_root) / "device_packs"
    return Path(__file__).resolve().parents[1] / "device_packs"


@dataclass(frozen=True)
class CaptureActionResult:
    ok: bool
    action: str
    status: dict[str, object] | None = None
    error_key: str | None = None


class CaptureWizardController:
    """Pure workflow controller used by the Tk wizard and host tests."""

    def __init__(self, profiles_root: Path | None = None) -> None:
        self.profiles_root = profiles_root or bundled_profiles_root()

    @staticmethod
    def _session_dir(value: Path) -> Path:
        if not value.is_absolute():
            raise DeviceCaptureSessionError("Session directory must be absolute.")
        return value

    def status(self, session_dir: Path) -> dict[str, object]:
        return public_capture_status(self._session_dir(session_dir))

    def create(self, session_dir: Path) -> dict[str, object]:
        return create_capture_session(self._session_dir(session_dir), self.profiles_root)

    def capture_adb(self, session_dir: Path, adb: Path) -> dict[str, object]:
        status = self.status(session_dir)
        captured = status["captured_transports"]
        if not isinstance(captured, list) or "adb" in captured:
            raise DeviceCaptureSessionError("ADB capture already exists or capture state is invalid.")
        profiles = discover_profiles(self.profiles_root)
        transport = ReadOnlyAdb(adb).inspect()
        unified = build_unified_report("adb", transport, profiles)
        return record_transport_report(
            session_dir,
            self.profiles_root,
            transport="adb",
            report=unified,
        )

    def capture_fastboot(
        self,
        session_dir: Path,
        fastboot: Path,
        *,
        include_partitions: bool = False,
    ) -> dict[str, object]:
        status = self.status(session_dir)
        captured = status["captured_transports"]
        if (
            not isinstance(captured, list)
            or "adb" not in captured
            or "fastboot" in captured
            or status.get("finalized") is True
        ):
            raise DeviceCaptureSessionError(
                "Fastboot capture requires one prior ADB capture and no final bundle."
            )
        profiles = discover_profiles(self.profiles_root)
        transport = ReadOnlyFastboot(fastboot).inspect(include_partitions=include_partitions)
        unified = build_unified_report("fastboot", transport, profiles)
        return record_transport_report(
            session_dir,
            self.profiles_root,
            transport="fastboot",
            report=unified,
        )

    def finalize(self, session_dir: Path) -> dict[str, object]:
        status = self.status(session_dir)
        captured = status["captured_transports"]
        if captured != ["adb", "fastboot"] or status.get("finalized") is True:
            raise DeviceCaptureSessionError(
                "Finalization requires exactly one ADB and one Fastboot capture."
            )
        return finalize_capture_session(session_dir, self.profiles_root)

    def verify(self, session_dir: Path) -> dict[str, object]:
        status = self.status(session_dir)
        if status.get("finalized") is not True:
            raise DeviceCaptureSessionError("Verification requires a finalized capture bundle.")
        return verify_capture_session(session_dir, self.profiles_root)

    def safe_action(
        self,
        action: str,
        operation: Callable[[], dict[str, object]],
    ) -> CaptureActionResult:
        try:
            return CaptureActionResult(True, action, operation(), None)
        except _CAPTURE_ERRORS:
            return CaptureActionResult(False, action, None, "capture_error")


class PhysicalCaptureWizard:
    """Tk Toplevel that keeps transport transitions explicit and owner-controlled."""

    def __init__(
        self,
        parent: tk.Misc,
        language: tk.StringVar,
        *,
        controller: CaptureWizardController | None = None,
    ) -> None:
        self.parent = parent
        self.language = language
        self.controller = controller or CaptureWizardController()
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.geometry("780x620")
        self.window.minsize(680, 560)
        self.window.configure(background="#02050A")
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.session_path = tk.StringVar(self.window)
        self.adb_path = tk.StringVar(self.window)
        self.fastboot_path = tk.StringVar(self.window)
        self.include_partitions = tk.BooleanVar(self.window, value=False)
        self.status: dict[str, object] | None = None
        self._busy = False
        self._closed = False
        self._labels: list[tuple[tk.Widget, str]] = []
        self._queue: Queue[CaptureActionResult] = Queue()
        self._language_trace = self.language.trace_add("write", self._language_changed)

        style = ttk.Style(self.window)
        style.configure("Capture.TFrame", background="#02050A")
        style.configure("Capture.TLabel", background="#02050A", foreground="#E9F7FF")
        style.configure(
            "CaptureTitle.TLabel",
            background="#02050A",
            foreground="#62E5FF",
            font=("TkDefaultFont", 18, "bold"),
        )
        style.configure(
            "CaptureNotice.TLabel",
            background="#07111C",
            foreground="#CFEFFF",
            padding=10,
        )
        style.configure("Capture.TButton", padding=(10, 6))
        style.configure("Capture.TCheckbutton", background="#02050A", foreground="#E9F7FF")

        outer = ttk.Frame(self.window, padding=14, style="Capture.TFrame")
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(8, weight=1)

        self._label(outer, "capture_title", style="CaptureTitle.TLabel").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8)
        )
        self._label(
            outer,
            "capture_notice",
            style="CaptureNotice.TLabel",
            wraplength=720,
        ).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 12))

        self._label(outer, "capture_session_path").grid(
            row=2, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Entry(outer, textvariable=self.session_path).grid(row=2, column=1, sticky="ew")
        self.new_button = self._button(outer, "capture_new_session", self.choose_new_session)
        self.new_button.grid(row=2, column=2, padx=(8, 4))
        self.open_button = self._button(
            outer,
            "capture_open_session",
            self.choose_existing_session,
        )
        self.open_button.grid(row=2, column=3)

        self._label(outer, "capture_adb_tool").grid(
            row=3, column=0, sticky="w", pady=(8, 0), padx=(0, 8)
        )
        ttk.Entry(outer, textvariable=self.adb_path).grid(
            row=3,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        self.adb_browse = self._button(
            outer,
            "capture_browse_tool",
            lambda: self.choose_tool("adb"),
        )
        self.adb_browse.grid(row=3, column=3, pady=(8, 0))

        self._label(outer, "capture_fastboot_tool").grid(
            row=4, column=0, sticky="w", pady=(8, 0), padx=(0, 8)
        )
        ttk.Entry(outer, textvariable=self.fastboot_path).grid(
            row=4,
            column=1,
            columnspan=2,
            sticky="ew",
            pady=(8, 0),
        )
        self.fastboot_browse = self._button(
            outer,
            "capture_browse_tool",
            lambda: self.choose_tool("fastboot"),
        )
        self.fastboot_browse.grid(row=4, column=3, pady=(8, 0))

        self.partition_check = ttk.Checkbutton(
            outer,
            text=self.tr("capture_partitions"),
            variable=self.include_partitions,
            style="Capture.TCheckbutton",
        )
        self._labels.append((self.partition_check, "capture_partitions"))
        self.partition_check.grid(row=5, column=1, columnspan=3, sticky="w", pady=(8, 0))

        actions = ttk.Frame(outer, style="Capture.TFrame")
        actions.grid(row=6, column=0, columnspan=4, sticky="ew", pady=12)
        self.create_button = self._button(actions, "capture_create", self.create_session)
        self.adb_button = self._button(actions, "capture_capture_adb", self.capture_adb)
        self.fastboot_button = self._button(
            actions,
            "capture_capture_fastboot",
            self.capture_fastboot,
        )
        self.finalize_button = self._button(actions, "capture_finalize", self.finalize_session)
        self.verify_button = self._button(actions, "capture_verify", self.verify_session)
        for index, button in enumerate(
            (
                self.create_button,
                self.adb_button,
                self.fastboot_button,
                self.finalize_button,
                self.verify_button,
            )
        ):
            button.pack(side="left", padx=(0 if index == 0 else 6, 0))

        self.manual_label = self._label(
            outer,
            "capture_manual_transition",
            style="CaptureNotice.TLabel",
            wraplength=720,
        )
        self.manual_label.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        self.output = tk.Text(
            outer,
            wrap="word",
            state="disabled",
            height=10,
            background="#07111C",
            foreground="#DDF6FF",
            insertbackground="#DDF6FF",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.output.grid(row=8, column=0, columnspan=4, sticky="nsew")

        footer = ttk.Frame(outer, style="Capture.TFrame")
        footer.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        self.busy_label = self._label(footer, "capture_ready")
        self.busy_label.pack(side="left")
        self.close_button = self._button(footer, "capture_close", self.close)
        self.close_button.pack(side="right")

        self.window.title(self.tr("capture_title"))
        self._render_status(None)
        self._refresh_buttons()

    def tr(self, key: str, **values: object) -> str:
        return translate(self.language.get(), key, **values)

    def _label(self, parent: tk.Misc, key: str, **kwargs: object) -> ttk.Label:
        label = ttk.Label(
            parent,
            text=self.tr(key),
            style=kwargs.pop("style", "Capture.TLabel"),
            **kwargs,
        )
        self._labels.append((label, key))
        return label

    def _button(
        self,
        parent: tk.Misc,
        key: str,
        command: Callable[[], None],
    ) -> ttk.Button:
        button = ttk.Button(
            parent,
            text=self.tr(key),
            command=command,
            style="Capture.TButton",
        )
        self._labels.append((button, key))
        return button

    def _language_changed(self, *_: object) -> None:
        if self._closed:
            return
        self.window.title(self.tr("capture_title"))
        for widget, key in self._labels:
            widget.configure(text=self.tr(key))
        self._render_status(self.status)

    def _session(self) -> Path:
        return Path(self.session_path.get())

    def choose_new_session(self) -> None:
        if self._busy:
            return
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title=self.tr("capture_choose_new_title"),
            initialfile="swirphoneos-capture",
        )
        if path:
            self.session_path.set(path)
            self.status = None
            self._render_status(None)
            self._refresh_buttons()

    def choose_existing_session(self) -> None:
        if self._busy:
            return
        path = filedialog.askdirectory(
            parent=self.window,
            title=self.tr("capture_open_title"),
            mustexist=True,
        )
        if not path:
            return
        self.session_path.set(path)
        result = self.controller.safe_action(
            "open",
            lambda: self.controller.status(Path(path)),
        )
        if result.ok:
            self.status = result.status
            self._render_status(self.status)
        else:
            self.status = None
            messagebox.showerror(
                "SwirPhoneOS",
                self.tr(result.error_key or "capture_error"),
                parent=self.window,
            )
        self._refresh_buttons()

    def choose_tool(self, transport: str) -> None:
        if self._busy:
            return
        key = "capture_tool_title_adb" if transport == "adb" else "capture_tool_title_fastboot"
        path = filedialog.askopenfilename(parent=self.window, title=self.tr(key))
        if path:
            (self.adb_path if transport == "adb" else self.fastboot_path).set(path)

    def _start(
        self,
        action: str,
        operation: Callable[[], dict[str, object]],
    ) -> None:
        if self._busy:
            return
        self._busy = True
        self.busy_label.configure(text=self.tr("capture_busy"))
        self._refresh_buttons()

        def worker() -> None:
            self._queue.put(self.controller.safe_action(action, operation))

        Thread(target=worker, name=f"swir-capture-{action}", daemon=True).start()
        self.window.after(80, self._poll)

    def _poll(self) -> None:
        if self._closed:
            return
        try:
            result = self._queue.get_nowait()
        except Empty:
            self.window.after(80, self._poll)
            return
        self._busy = False
        if result.ok:
            self.status = result.status
            self._render_status(self.status)
            self.busy_label.configure(text=self.tr(f"capture_done_{result.action}"))
        else:
            self.busy_label.configure(text=self.tr("capture_ready"))
            messagebox.showerror(
                "SwirPhoneOS",
                self.tr(result.error_key or "capture_error"),
                parent=self.window,
            )
        self._refresh_buttons()

    def create_session(self) -> None:
        self._start("create", lambda: self.controller.create(self._session()))

    def capture_adb(self) -> None:
        self._start(
            "adb",
            lambda: self.controller.capture_adb(
                self._session(),
                Path(self.adb_path.get()),
            ),
        )

    def capture_fastboot(self) -> None:
        self._start(
            "fastboot",
            lambda: self.controller.capture_fastboot(
                self._session(),
                Path(self.fastboot_path.get()),
                include_partitions=self.include_partitions.get(),
            ),
        )

    def finalize_session(self) -> None:
        self._start("finalize", lambda: self.controller.finalize(self._session()))

    def verify_session(self) -> None:
        self._start("verify", lambda: self.controller.verify(self._session()))

    def _render_status(self, status: dict[str, object] | None) -> None:
        if status is None:
            text = self.tr("capture_state_new")
        else:
            captured = status.get("captured_transports")
            if isinstance(captured, list) and captured:
                names = ", ".join(
                    self.tr(f"capture_transport_{item}")
                    for item in captured
                    if item in {"adb", "fastboot"}
                )
            else:
                names = self.tr("none")
            text = self.tr(
                "capture_status_summary",
                session=status.get("session_id", ""),
                captures=names,
                finalized=self.tr("yes") if status.get("finalized") is True else self.tr("no"),
                state=self.tr(
                    "capture_state_finalized"
                    if status.get("finalized") is True
                    else "capture_state_in_progress"
                ),
            )
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _refresh_buttons(self) -> None:
        for button in (
            self.create_button,
            self.adb_button,
            self.fastboot_button,
            self.finalize_button,
            self.verify_button,
            self.new_button,
            self.open_button,
            self.adb_browse,
            self.fastboot_browse,
            self.close_button,
        ):
            button.state(["disabled"] if self._busy else ["!disabled"])
        if self._busy:
            return

        status = self.status
        if status is None:
            for button in (
                self.adb_button,
                self.fastboot_button,
                self.finalize_button,
                self.verify_button,
            ):
                button.state(["disabled"])
            return

        self.create_button.state(["disabled"])
        captured = status.get("captured_transports")
        captures = captured if isinstance(captured, list) else []
        finalized = status.get("finalized") is True
        self.adb_button.state(["disabled"] if "adb" in captures or finalized else ["!disabled"])
        self.fastboot_button.state(
            ["!disabled"] if captures == ["adb"] and not finalized else ["disabled"]
        )
        self.finalize_button.state(
            ["!disabled"]
            if captures == ["adb", "fastboot"] and not finalized
            else ["disabled"]
        )
        self.verify_button.state(["!disabled"] if finalized else ["disabled"])

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.language.trace_remove("write", self._language_trace)
        except tk.TclError:
            pass
        self.window.destroy()
