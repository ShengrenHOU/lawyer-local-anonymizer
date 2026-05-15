from __future__ import annotations

from pathlib import Path

from legal_anonymizer.gui import run_app


def main() -> int:
    root = Path.home() / "律师本地匿名化助手"
    return run_app(root)


if __name__ == "__main__":
    raise SystemExit(main())

