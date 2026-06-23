from __future__ import annotations

import os
import sys

from patchbay.tui.app import main


def run():
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()


if __name__ == "__main__":
    run()
