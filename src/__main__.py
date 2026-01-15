"""Entry point for Grove application."""

import argparse
import sys
from pathlib import Path
from textual.app import App, ComposeResult

from .app import GroveApp
from .clone import clone_repository
from .config import (
    config_exists,
    detect_potential_repositories,
    add_repository,
    load_config,
    get_repositories,
    find_repo_for_directory,
    set_active_repo,
    update_last_used,
    ConfigError,
)
from .screens import SetupWizardScreen, RepositorySelectionScreen


class SetupApp(App):
    """Minimal app for running the setup wizard."""

    def __init__(self, detected_repos: list) -> None:
        """Initialize setup app with detected repositories."""
        super().__init__()
        self.detected_repos = detected_repos
        self.selected_repo: str | None = None

    def on_mount(self) -> None:
        """Show setup wizard when app starts."""

        def handle_wizard_result(result: str | None) -> None:
            """Handle the result from the setup wizard."""
            self.selected_repo = result
            self.exit()

        self.push_screen(SetupWizardScreen(self.detected_repos), handle_wizard_result)

    def compose(self) -> ComposeResult:
        """Empty compose - wizard is shown as modal."""
        return []


class RepositorySelectionApp(App):
    """Minimal app for repository selection screen."""

    def __init__(self, repositories: list[dict[str, str]]) -> None:
        """Initialize with list of repositories."""
        super().__init__()
        self.repositories = repositories
        self.selected_repo: str | None = None

    def on_mount(self) -> None:
        """Show repository selection screen when app starts."""

        def handle_selection(result: str | None) -> None:
            """Handle the result from repository selection."""
            self.selected_repo = result
            self.exit()

        self.push_screen(RepositorySelectionScreen(self.repositories), handle_selection)

    def compose(self) -> ComposeResult:
        """Empty compose - screen is shown as modal."""
        return []


def select_repository_smart() -> Path | None:
    """Smart repository selection based on cwd and last_used.

    Returns:
        Path to selected repository, or None if user quit
    """
    repos = get_repositories()

    if not repos:
        return None  # Trigger setup wizard

    # Priority 1: Check if current directory is inside any configured repo
    cwd = Path.cwd()
    repo_path = find_repo_for_directory(cwd)
    if repo_path:
        return repo_path

    # Priority 2: Use last_used if available
    try:
        config = load_config()
        last_used = config.get("grove", {}).get("last_used")
        if last_used and any(r["path"] == last_used for r in repos):
            return Path(last_used)
    except ConfigError:
        pass

    # Priority 3: Show selection screen
    app = RepositorySelectionApp(repos)
    app.run()
    return Path(app.selected_repo) if app.selected_repo else None


def main() -> None:
    """Main entry point with CLI argument parsing and repository selection loop."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        prog="grove", description="Git Worktree and Tmux Session Manager"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Clone subcommand
    clone_parser = subparsers.add_parser(
        "clone", help="Clone a repository and set up Grove structure"
    )
    clone_parser.add_argument("url", help="Git repository URL to clone")
    clone_parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Target directory name (default: repository name from URL)",
    )

    args = parser.parse_args()

    # Handle clone command
    if args.command == "clone":
        exit_code = clone_repository(args.url, args.name)
        sys.exit(exit_code)

    # TUI launch logic
    while True:
        # Check if config exists
        if not config_exists():
            # First-time setup: show wizard
            detected = detect_potential_repositories()
            setup_app = SetupApp(detected)
            setup_app.run()

            if setup_app.selected_repo is None:
                print("Setup cancelled.", file=sys.stderr)
                sys.exit(0)

            # Add first repository
            try:
                add_repository(setup_app.selected_repo)
                print(f"Added repository: {Path(setup_app.selected_repo).name}")
            except ConfigError as e:
                print(f"Failed to add repository: {e}", file=sys.stderr)
                sys.exit(1)

        # Smart repository selection
        try:
            repo_path = select_repository_smart()
        except ConfigError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

        if repo_path is None:
            # User quit from selection screen
            sys.exit(0)

        # Set active repository and update last_used
        try:
            set_active_repo(repo_path)
            update_last_used(str(repo_path))
        except ConfigError as e:
            print(f"Failed to set active repository: {e}", file=sys.stderr)
            sys.exit(1)

        # Start Grove app
        app = GroveApp()
        app.run()

        # Check if user wants to switch repos
        if not hasattr(app, "restart_with_different_repo") or not app.restart_with_different_repo:
            # Normal exit, don't restart
            break


if __name__ == "__main__":
    main()
