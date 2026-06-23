from __future__ import annotations

import os
import sys

from patchbay.tui.app import PatchbayApp


def main():
    """Entry point for the TUI application."""
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    app = PatchbayApp()
    app.run()


if __name__ == "__main__":
    main()
