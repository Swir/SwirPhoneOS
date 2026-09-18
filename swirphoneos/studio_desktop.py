"""Frozen SwirPhoneStudio desktop shell with read-only evidence tools."""
from __future__ import annotations

import argparse
import sys
import tkinter as tk

from .i18n import translate
from .studio import Studio
from .studio_capture_wizard import PhysicalCaptureWizard


def install_capture_menu(root: tk.Tk, app: Studio) -> tuple[tk.Menu, str]:
    """Install the physical capture launcher and keep it localized."""
    menu = tk.Menu(root, tearoff=False)
    tools = tk.Menu(menu, tearoff=False)

    def open_capture() -> None:
        PhysicalCaptureWizard(root, app.language)

    tools.add_command(label=translate(app.language.get(), "capture_menu"), command=open_capture)
    menu.add_cascade(label=translate(app.language.get(), "capture_tools_menu"), menu=tools)
    root.configure(menu=menu)

    def refresh(*_: object) -> None:
        tools.entryconfigure(0, label=translate(app.language.get(), "capture_menu"))
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
