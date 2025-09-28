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
        directories = get_worktree_directories()
        if directories:
            for directory in directories:
                yield ListItem(Label(directory))
        else:
            yield ListItem(Label("No directories found"))

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

def get_worktree_directories():
    """Get directories at the same level as .bare directory, excluding hidden directories."""
    current_path = Path.cwd()
    bare_parent = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return []

    # Get all directories at the same level as .bare, excluding hidden ones
    directories = []
    for item in bare_parent.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)

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
