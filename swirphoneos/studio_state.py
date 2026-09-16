"""Display-independent state and private, create-only diagnostic report export."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Callable
import json
import os

from .diagnostics import DiagnosticError, ReadOnlyAdb, summarize


@dataclass(frozen=True)
class ScanResult:
    report_json: str | None = None
    error_key: str | None = None


def report_json(report: dict[str, object]) -> str:
    """Accept only the core's known schema. Never export extra private fields."""
    expected = summarize({})
    if set(report) != set(expected):
        raise ValueError("Unexpected diagnostic report fields.")
    for key in ("schema_version", "source", "swirphoneos_support", "flash_allowed", "warnings"):
        if type(report[key]) is not type(expected[key]) or report[key] != expected[key]:
            raise ValueError("Diagnostic report cannot change safety or provenance fields.")
    for key in ("treble_reported", "dynamic_partitions_reported"):
        if report[key] is not None and type(report[key]) is not bool:
            raise ValueError("Invalid reported boolean.")
    if report["bootloader_reported"] not in ("locked", "unlocked", "unknown"):
        raise ValueError("Invalid reported bootloader state.")
    for key in ("manufacturer", "model", "codename", "abi", "android_release",
                "reported_security_patch", "slot_suffix_reported"):
        value = report[key]
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 256
            or not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError("Invalid reported property value.")
    return json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n"


def save_report(destination: Path, payload: str) -> None:
    """Create a new local JSON file; never overwrite or follow a target symlink."""
    if not destination.is_absolute() or destination.suffix.lower() != ".json":
        raise ValueError("Choose an absolute .json destination.")
    if len(payload) > 16384:
        raise ValueError("Report is too large.")
    normalized = report_json(json.loads(payload)).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(destination, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(normalized)
    # Device-reported model/manufacturer text is not guaranteed to be anonymous.
    # The UI asks the owner to review the report before sharing it publicly.


class DiagnosticSession:
    """UI-thread-owned state; one daemon worker publishes immutable JSON only."""

    def __init__(self, inspector: Callable[[Path], dict[str, object]] | None = None):
        self._inspector = inspector or (lambda path: ReadOnlyAdb(path).inspect())
        self._results: Queue[ScanResult] = Queue(maxsize=1)
        self.busy = False
        self.report: str | None = None

    def start(self, executable: Path) -> bool:
        if self.busy:
            return False
        self.report = None  # A failed new attempt must not leave an old export available.
        self.busy = True
        try:
            Thread(target=self._worker, args=(executable,), daemon=True).start()
        except RuntimeError:
            self._results.put_nowait(ScanResult(error_key="unexpected"))
        return True

    def _worker(self, executable: Path) -> None:
        try:
            result = ScanResult(report_json=report_json(self._inspector(executable)))
        except DiagnosticError:
            result = ScanResult(error_key="scan_failed")
        except Exception:
            # Never send paths, subprocess output, serials or raw exception text to Tk.
            result = ScanResult(error_key="unexpected")
        self._results.put_nowait(result)

    def poll(self) -> ScanResult | None:
        try:
            result = self._results.get_nowait()
        except Empty:
            return None
        self.busy = False
        self.report = result.report_json
        return result
