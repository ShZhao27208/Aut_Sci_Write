"""Backward-compatible interactive entry point."""

from .main import main, run_interactive


def run():
    return run_interactive()


if __name__ == "__main__":
    main()
