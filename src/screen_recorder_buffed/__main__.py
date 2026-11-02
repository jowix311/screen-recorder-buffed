"""Entry point: `python -m screen_recorder_buffed` or the `screen-recorder-buffed` script."""

from __future__ import annotations

import sys

from screen_recorder_buffed.app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
