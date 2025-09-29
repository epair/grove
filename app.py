import os
import subprocess
import sys
import time
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView, ListItem, Label, Markdown, Input, Button
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.reactive import reactive

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

class MetadataDisplay(Markdown):
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
            "",
            f"**Last Commit:** {git_info['commit_message']}",
            "",
            f"**Date:** {git_info['commit_date']}",
            "",
            f"**Committer:** {git_info['committer']}",
        ])

        self.update("\n".join(content_parts))

class WorktreeFormScreen(ModalScreen[dict[str, str] | None]):
    """A modal screen for creating new worktrees."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the form layout."""
        with Vertical(id="dialog"):
            yield Label("Create New Worktree", id="title")
            yield Label("Prefix:")
            yield Input(value="ep/", placeholder="ep/", id="prefix_input")
            yield Label("Name:")
            yield Input(placeholder="Enter worktree name", id="name_input")
            with Center():
                yield Button("Create", variant="primary", id="create_button")
                yield Button("Cancel", variant="default", id="cancel_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "create_button":
            prefix = self.query_one("#prefix_input", Input).value
            name = self.query_one("#name_input", Input).value

            if not name.strip():
                return  # Don't submit if name is empty

            self.dismiss({"prefix": prefix, "name": name})
        elif event.button.id == "cancel_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "name_input":
            # Trigger create button when Enter is pressed in name field
            prefix = self.query_one("#prefix_input", Input).value
            name = event.input.value

            if name.strip():
                self.dismiss({"prefix": prefix, "name": name})

    def action_cancel(self) -> None:
        """Cancel the form and return to main app."""
        self.dismiss(None)

class ConfirmDeleteScreen(ModalScreen[bool]):
    """A modal screen for confirming worktree deletion."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No")
    ]

    def __init__(self, worktree_name: str) -> None:
        super().__init__()
        self.worktree_name = worktree_name

    def compose(self) -> ComposeResult:
        """Create the confirmation dialog layout."""
        with Vertical(id="delete_dialog"):
            yield Label("Delete Worktree", id="delete_title")
            yield Label(f"Are you sure you want to delete '{self.worktree_name}'?", id="delete_message")
            yield Label("This action cannot be undone.", id="delete_warning")
            with Center():
                yield Button("Yes (y)", variant="error", id="yes_button")
                yield Button("No (n)", variant="default", id="no_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "yes_button":
            self.dismiss(True)
        elif event.button.id == "no_button":
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm deletion."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel deletion."""
        self.dismiss(False)

class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("n", "new_worktree", "New worktree"),
        ("d", "delete_worktree", "Delete worktree")
    ]

    selected_worktree = reactive("")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        yield MetadataDisplay("Select a worktree to view its metadata.", id="body")
        yield Footer()
    
    def on_mount(self) -> None:
        self.theme = "tokyo-night"

    def action_new_worktree(self) -> None:
        """An action to create a new worktree."""
        self.push_screen(WorktreeFormScreen(), self.handle_worktree_creation)

    def action_delete_worktree(self) -> None:
        """An action to delete the selected worktree."""
        if not self.selected_worktree:
            self.notify("No worktree selected", severity="warning")
            return

        self.push_screen(ConfirmDeleteScreen(self.selected_worktree), self.handle_worktree_deletion)

    def handle_worktree_creation(self, form_data: dict[str, str] | None) -> None:
        """Handle the result from the worktree creation form."""
        if form_data is None:
            return  # User cancelled

        prefix = form_data["prefix"]
        name = form_data["name"]

        # Set environment variable and run worktree-manager command
        env = os.environ.copy()
        env["WORKTREE_PREFIX"] = prefix

        try:
            # Run worktree-manager add command
            result = subprocess.run(
                ["worktree-manager", "add", name],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.notify(f"Failed to create worktree: {result.stderr}", severity="error")
                return

            # Wait a moment for the worktree to be created
            time.sleep(1)

            # Find the worktree root directory (where .bare is located)
            current_path = Path.cwd()
            worktree_root = None

            if (current_path / ".bare").is_dir():
                worktree_root = current_path
            elif (current_path.parent / ".bare").is_dir():
                worktree_root = current_path.parent

            if worktree_root is None:
                self.notify("Could not find worktree root directory", severity="error")
                return

            # Run tmux-sessionizer command
            worktree_path = worktree_root / name
            sessionizer_result = subprocess.run(
                ["tmux-sessionizer", str(worktree_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if sessionizer_result.returncode == 0:
                # Success - exit the application
                self.exit()
            else:
                self.notify(f"Worktree created but failed to start tmux session: {sessionizer_result.stderr}", severity="warning")

        except subprocess.TimeoutExpired:
            self.notify("Command timed out", severity="error")
        except FileNotFoundError as e:
            self.notify(f"Command not found: {e.filename}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")

    def handle_worktree_deletion(self, confirmed: bool | None) -> None:
        """Handle the result from the worktree deletion confirmation."""
        if confirmed is None or not confirmed:
            return  # User cancelled

        worktree_name = self.selected_worktree
        if not worktree_name:
            return

        # Extract prefix from worktree name
        # Assume prefix format is "prefix/name" -> extract "prefix/"
        prefix = ""
        if "/" in worktree_name:
            prefix = worktree_name.split("/")[0] + "/"

        # Set environment variable and run worktree-manager remove command
        env = os.environ.copy()
        env["WORKTREE_PREFIX"] = prefix

        try:
            # Run worktree-manager remove command
            result = subprocess.run(
                ["worktree-manager", "remove", worktree_name],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.notify(f"Failed to delete worktree: {result.stderr}", severity="error")
                return

            # Check if there's a tmux session with the same name and kill it
            try:
                # Check if session exists first
                session_check = subprocess.run(
                    ['tmux', 'has-session', '-t', worktree_name],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if session_check.returncode == 0:
                    # Session exists, kill it
                    kill_result = subprocess.run(
                        ['tmux', 'kill-session', '-t', worktree_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if kill_result.returncode == 0:
                        self.notify(f"Worktree '{worktree_name}' and its tmux session deleted successfully", severity="information")
                    else:
                        self.notify(f"Worktree deleted but failed to kill tmux session: {kill_result.stderr}", severity="warning")
                else:
                    self.notify(f"Worktree '{worktree_name}' deleted successfully", severity="information")

            except (FileNotFoundError, subprocess.SubprocessError):
                # tmux not available or other error, but worktree was deleted successfully
                self.notify(f"Worktree '{worktree_name}' deleted successfully", severity="information")

            # Refresh the sidebar by recreating it
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.clear()
            directories = get_worktree_directories()
            sessions = get_active_tmux_sessions()

            if directories:
                for directory in directories:
                    icon = "●" if directory in sessions else "○"
                    sidebar.append(ListItem(Label(f"{icon} {directory}")))
            else:
                sidebar.append(ListItem(Label("No directories found")))

            # Clear selection if the deleted worktree was selected
            if self.selected_worktree == worktree_name:
                self.selected_worktree = ""

        except subprocess.TimeoutExpired:
            self.notify("Command timed out", severity="error")
        except FileNotFoundError as e:
            self.notify(f"Command not found: {e.filename}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")

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
