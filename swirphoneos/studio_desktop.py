"""Frozen SwirPhoneStudio desktop shell with read-only evidence tools."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tkinter as tk

from .i18n import translate
from .studio import Studio
from .studio_capture_wizard import PhysicalCaptureWizard
from .studio_device_inventory import DeviceInventoryEvidence, collect_device_inventory
from .studio_toolchain import ToolDiscovery, discover_android_tool


def detect_studio_tool(app: Studio) -> ToolDiscovery:
    """Populate the current transport path after an explicit owner request."""
    result = discover_android_tool(app.transport_code(), include_path=True)
    if result.path is not None:
        app.tool_path.set(str(result.path))
        app.status_key = "tool_found"
    else:
        # Preserve an existing manually reviewed path when auto-discovery fails.
        app.status_key = "tool_not_found"
    app.update_status()
    return result


def prefill_capture_tools(wizard: PhysicalCaptureWizard) -> tuple[ToolDiscovery, ToolDiscovery]:
    """Prefill conventional SDK paths without executing either transport tool."""
    adb = discover_android_tool("adb", include_path=False)
    fastboot = discover_android_tool("fastboot", include_path=False)
    if adb.path is not None and not wizard.adb_path.get():
        wizard.adb_path.set(str(adb.path))
    if fastboot.path is not None and not wizard.fastboot_path.get():
        wizard.fastboot_path.set(str(fastboot.path))
    return adb, fastboot


def render_device_inventory(app: Studio, evidence: DeviceInventoryEvidence) -> str:
    """Render privacy-minimized inventory data through the shared locale catalog."""
    lines = [app.tr("inventory_title")]
    if not evidence.observations:
        lines.append(app.tr("inventory_none"))
        return "\n\n".join(lines)
    for item in evidence.observations:
        lines.append(
            app.tr(
                "inventory_item",
                transport=item.transport.upper(),
                state=item.state,
                identifier=item.identifier_sha256[:12],
                model=item.model or "—",
            )
        )
    return "\n".join(lines)


def inspect_current_devices(app: Studio) -> DeviceInventoryEvidence | None:
    """Explicitly run the current transport's read-only inventory command."""
    if app.session.busy:
        return None
    raw_path = app.tool_path.get().strip()
    if not raw_path:
        app.status_key = "tool_not_found"
        app.update_status()
        return None

    transport = app.transport_code()
    kwargs = {f"{transport}_path": Path(raw_path)}
    try:
        evidence = collect_device_inventory(**kwargs)
    except (OSError, RuntimeError, TimeoutError, ValueError):
        app.status_key = "inventory_failed"
        app.update_status()
        app.show_report(app.tr("inventory_failed"))
        return None

    app.status_key = "inventory_complete"
    app.update_status()
    app.show_report(render_device_inventory(app, evidence))
    return evidence


def install_capture_menu(root: tk.Tk, app: Studio) -> tuple[tk.Menu, str]:
    """Install localized evidence/tool launchers while keeping device actions explicit."""
    menu = tk.Menu(root, tearoff=False)
    tools = tk.Menu(menu, tearoff=False)

    def open_capture() -> None:
        wizard = PhysicalCaptureWizard(root, app.language)
        prefill_capture_tools(wizard)

    def detect_tool() -> None:
        if app.session.busy:
            return
        detect_studio_tool(app)

    def inspect_devices() -> None:
        inspect_current_devices(app)

    # Keep the existing capture action at index 0 for compatibility with
    # embeddings/tests, then append explicit read-only discovery/inventory actions.
    tools.add_command(label=translate(app.language.get(), "capture_menu"), command=open_capture)
    tools.add_command(label=translate(app.language.get(), "studio_detect_tool"), command=detect_tool)
    tools.add_command(label=translate(app.language.get(), "studio_inspect_devices"), command=inspect_devices)
    menu.add_cascade(label=translate(app.language.get(), "capture_tools_menu"), menu=tools)
    root.configure(menu=menu)

    def refresh(*_: object) -> None:
        tools.entryconfigure(0, label=translate(app.language.get(), "capture_menu"))
        tools.entryconfigure(1, label=translate(app.language.get(), "studio_detect_tool"))
        tools.entryconfigure(2, label=translate(app.language.get(), "studio_inspect_devices"))
        menu.entryconfigure(0, label=translate(app.language.get(), "capture_tools_menu"))

    trace_id = app.language.trace_add("write", refresh)
    return menu, trace_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only SwirPhoneOS Flash Studio developer UI.")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Open and close the UI without using Android SDK tools.",
    )
    args = parser.parse_args(argv)
    try:
        root = tk.Tk()
    except tk.TclError:
        print(
            "A graphical desktop and Tk are required. No device operation was attempted.",
            file=sys.stderr,
        )
        return 1

    app = Studio(root)
    install_capture_menu(root, app)
    if args.smoke_test:
        root.after(300, app.close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
