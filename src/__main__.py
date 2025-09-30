"""Entry point for Grove application."""

import sys

from .app import GroveApp
from .utils import is_bare_git_repository


def main() -> None:
    """Main entry point for Grove application."""
    if not is_bare_git_repository():
        print("Error: Grove must be run from a bare git repository (directory containing '.bare' subdirectory)", file=sys.stderr)
        sys.exit(1)

    app = GroveApp()
    app.run()


if __name__ == "__main__":
    main()