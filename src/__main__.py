"""Entry point for Grove application."""

import sys
from textual.app import App, ComposeResult

from .app import GroveApp
from .config import config_exists, detect_potential_repositories, save_config, load_config, ConfigError
from .screens import SetupWizardScreen


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


def main() -> None:
    """Main entry point for Grove application."""
    # Check if config exists
    if not config_exists():
        # Run setup wizard
        detected = detect_potential_repositories()
        setup_app = SetupApp(detected)
        setup_app.run()

        # Check if user selected a repo
        if setup_app.selected_repo is None:
            print("Setup cancelled. Grove requires a configured repository to run.", file=sys.stderr)
            sys.exit(1)

        # Save config
        try:
            save_config(setup_app.selected_repo)
            print(f"Configuration saved: {setup_app.selected_repo}")
        except ConfigError as e:
            print(f"Failed to save configuration: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate config
    try:
        config = load_config()
        # Config is valid, continue
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("\nPlease fix your configuration file at ~/.config/grove/config", file=sys.stderr)
        print("or delete it to run the setup wizard again.", file=sys.stderr)
        sys.exit(1)

    # Start main app
    app = GroveApp()
    app.run()


if __name__ == "__main__":
    main()