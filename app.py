import os
import subprocess
import sys
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView, ListItem, Label
from textual.reactive import reactive

TEXT = """\
Docking a widget removes it from the layout and fixes its position, aligned to either the top, right, bottom, or left edges of a container.

Docked widgets will not scroll out of view, making them ideal for sticky headers, footers, and sidebars.

"""

class Sidebar(ListView):
    def compose(self) -> ComposeResult:
        directories = get_worktree_directories()
        sessions = get_active_tmux_sessions()

        if directories:
            for directory in directories:
                icon = "●" if directory in sessions else "○"
                yield ListItem(Label(f"{icon} {directory}"))
        else:
            yield ListItem(Label("No directories found"))

def is_bare_git_repository() -> bool:
    """Check if current directory or parent contains a bare git repository."""
    current_path = Path.cwd()

    # Check current directory for .bare subdirectory
    if (current_path / ".bare").is_dir():
        return True

    # Check parent directory for .bare subdirectory
    if (current_path.parent / ".bare").is_dir():
        return True

    return False

def get_worktree_directories() -> list[str]:
    """Get directories at the same level as .bare directory, excluding hidden directories."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return []

    # Get all directories at the same level as .bare, excluding hidden ones
    directories: list[str] = []
    for item in bare_parent.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            directories.append(item.name)

    return sorted(directories)

def get_active_tmux_sessions() -> set[str]:
    """Get names of all active tmux sessions using tmux format strings."""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_name}'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return set(result.stdout.strip().split('\n'))
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return set()

def get_worktree_metadata(worktree_name: str) -> dict[str, str]:
    """Get metadata for a worktree from .grove/metadata/{worktree}/ directory."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return {}

    metadata_dir = bare_parent / ".grove" / "metadata" / worktree_name
    if not metadata_dir.exists():
        return {}

    metadata = {}
    for filename in ["description.md", "pr.md", "notes.md"]:
        file_path = metadata_dir / filename
        if file_path.exists():
            try:
                metadata[filename[:-3]] = file_path.read_text().strip()
            except (IOError, OSError):
                metadata[filename[:-3]] = ""
        else:
            metadata[filename[:-3]] = ""

    return metadata

def get_worktree_git_info(worktree_name: str) -> dict[str, str]:
    """Get git information for a worktree (last commit message, date, committer)."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    worktree_path = bare_parent / worktree_name
    if not worktree_path.exists():
        return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

    try:
        # Get last commit info using git log with format
        result = subprocess.run(
            ['git', '-C', str(worktree_path), 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            return {
                "commit_message": lines[0] if len(lines) > 0 else "N/A",
                "commit_date": lines[1] if len(lines) > 1 else "N/A",
                "committer": lines[2] if len(lines) > 2 else "N/A"
            }
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    return {"commit_message": "N/A", "commit_date": "N/A", "committer": "N/A"}

class MetadataDisplay(Static):
    """Widget to display worktree metadata and git information."""

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        if not worktree_name:
            self.update("Select a worktree to view its metadata.")
            return

        # Get metadata and git info
        metadata = get_worktree_metadata(worktree_name)
        git_info = get_worktree_git_info(worktree_name)

        # Format the content
        content_parts = [
            f"# {worktree_name}",
            "",
        ]

        # Add description if available
        if metadata.get("description"):
            content_parts.extend([
                "## Description",
                metadata["description"],
                "",
            ])
        else:
            content_parts.extend([
                "## Description",
                "*No description available*",
                "",
            ])

        # Add PR info if available
        if metadata.get("pr"):
            content_parts.extend([
                "## Pull Request Info",
                metadata["pr"],
                "",
            ])
        else:
            content_parts.extend([
                "## Pull Request Info",
                "*No PR information available*",
                "",
            ])

        # Add notes if available
        if metadata.get("notes"):
            content_parts.extend([
                "## Notes",
                metadata["notes"],
                "",
            ])
        else:
            content_parts.extend([
                "## Notes",
                "*No notes available*",
                "",
            ])

        # Add git information
        content_parts.extend([
            "## Git Information",
            f"**Last Commit:** {git_info['commit_message']}",
            f"**Date:** {git_info['commit_date']}",
            f"**Committer:** {git_info['committer']}",
        ])

        self.update("\n".join(content_parts))

class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "app.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    selected_worktree = reactive("")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        yield MetadataDisplay("Select a worktree to view its metadata.", id="body")
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def on_list_view_highlighted(self, message: ListView.Highlighted) -> None:
        """Handle when a worktree is highlighted in the sidebar."""
        if message.item and message.item.query(Label):
            label = message.item.query_one(Label)
            # Extract worktree name from label text (remove icon prefix)
            label_text = str(label.content)
            if " " in label_text:
                worktree_name = label_text.split(" ", 1)[1]
                self.selected_worktree = worktree_name

    def watch_selected_worktree(self, selected_worktree: str) -> None:
        """Update metadata display when selected worktree changes."""
        metadata_display = self.query_one("#body", MetadataDisplay)
        metadata_display.update_content(selected_worktree)


if __name__ == "__main__":
    if not is_bare_git_repository():
        print("Error: Grove must be run from a bare git repository (directory containing '.bare' subdirectory)", file=sys.stderr)
        sys.exit(1)

    app = GroveApp()
    app.run()
