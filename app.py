import os
import sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView, ListItem, Label

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""

class Sidebar(ListView):
    def compose(self) -> ComposeResult:
        yield ListItem(Label("One"))
        yield ListItem(Label("Two"))
        yield ListItem(Label("Three"))

def is_bare_git_repository():
    """Check if current directory or parent contains a bare git repository."""
    current_path = Path.cwd()

    # Check current directory for .bare subdirectory
    if (current_path / ".bare").is_dir():
        return True

    # Check parent directory for .bare subdirectory
    if (current_path.parent / ".bare").is_dir():
        return True

    return False

class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "app.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        yield Static(TEXT * 10, id="body")
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == "__main__":
    if not is_bare_git_repository():
        print("Error: Grove must be run from a bare git repository (directory containing '.bare' subdirectory)", file=sys.stderr)
        sys.exit(1)

    app = GroveApp()
    app.run()
