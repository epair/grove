import os
import subprocess
import sys
import time
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, ListView, ListItem, Label, Markdown, Input, Button, Checkbox
from textual.containers import Center, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual.binding import Binding

class Sidebar(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Move down", show=False),
        Binding("k", "cursor_up", "Move up", show=False),
    ]

    def compose(self) -> ComposeResult:
        directories = get_worktree_directories()
        sessions = get_active_tmux_sessions()
        pr_worktrees = get_worktree_pr_status()

        if directories:
            for directory in directories:
                icon = "●" if directory in sessions else "○"
                pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                yield ListItem(Label(f"{icon}{pr_indicator} {directory}"))
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

def get_worktree_pr_status() -> set[str]:
    """Get names of worktrees that have a PR published."""
    current_path = Path.cwd()
    bare_parent: Path | None = None

    # Find where the .bare directory is located
    if (current_path / ".bare").is_dir():
        bare_parent = current_path
    elif (current_path.parent / ".bare").is_dir():
        bare_parent = current_path.parent

    if bare_parent is None:
        return set()

    # Check each worktree for .env file with WORKTREE_PR_PUBLISHED=true
    pr_worktrees: set[str] = set()
    directories = get_worktree_directories()

    for directory in directories:
        env_file = bare_parent / directory / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text()
                # Check if WORKTREE_PR_PUBLISHED=true is in the file
                for line in content.strip().split('\n'):
                    if line.strip() == 'WORKTREE_PR_PUBLISHED=true':
                        pr_worktrees.add(directory)
                        break
            except (IOError, OSError):
                pass

    return pr_worktrees

def check_remote_branch_exists(worktree_path: Path) -> bool:
    """Check if the remote upstream branch exists for a worktree.

    Returns True if remote branch exists, False if it's gone or there's no upstream.
    """
    try:
        # Use git status to check if upstream branch is gone
        result = subprocess.run(
            ['git', '-C', str(worktree_path), 'status', '-b', '--porcelain'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0 and result.stdout:
            # Check if the first line contains [gone]
            first_line = result.stdout.strip().split('\n')[0]
            if '[gone]' in first_line:
                return False
            # If there's tracking info without [gone], the branch exists
            if '...' in first_line:
                return True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    # If we can't determine, assume it exists to be safe
    return True

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

class PRFormScreen(ModalScreen[dict[str, str | list[str]] | None]):
    """A modal screen for creating a pull request."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Create the PR form layout."""
        with Vertical(id="pr_dialog"):
            yield Label("Create Pull Request", id="pr_title")
            yield Label("PR Title:")
            yield Input(placeholder="Enter PR title", id="pr_title_input")
            yield Label("Select Reviewers:", id="reviewers_label")

            # Two-column layout for reviewers
            with Horizontal(id="reviewers_container"):
                with Vertical(classes="reviewer_column"):
                    yield Checkbox("njm", value=True, id="checkbox_njm")
                    yield Checkbox("swlkr", id="checkbox_swlkr")
                    yield Checkbox("daviswahl", id="checkbox_daviswahl")
                with Vertical(classes="reviewer_column"):
                    yield Checkbox("BryceFrye", id="checkbox_BryceFrye")
                    yield Checkbox("neddenriep", id="checkbox_neddenriep")
                    yield Checkbox("gorilla076", id="checkbox_gorilla076")

            with Center():
                yield Button("Create PR", variant="primary", id="create_pr_button")
                yield Button("Cancel", variant="default", id="cancel_pr_button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "create_pr_button":
            title = self.query_one("#pr_title_input", Input).value

            if not title.strip():
                return  # Don't submit if title is empty

            # Collect selected reviewers
            reviewers = []
            for reviewer in ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]:
                checkbox = self.query_one(f"#checkbox_{reviewer}", Checkbox)
                if checkbox.value:
                    reviewers.append(reviewer)

            self.dismiss({"title": title, "reviewers": reviewers})
        elif event.button.id == "cancel_pr_button":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input fields."""
        if event.input.id == "pr_title_input":
            title = event.input.value

            if title.strip():
                # Collect selected reviewers
                reviewers = []
                for reviewer in ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]:
                    checkbox = self.query_one(f"#checkbox_{reviewer}", Checkbox)
                    if checkbox.value:
                        reviewers.append(reviewer)

                self.dismiss({"title": title, "reviewers": reviewers})

    def action_cancel(self) -> None:
        """Cancel the form and return to main app."""
        self.dismiss(None)

class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_worktree", "New worktree"),
        ("d", "delete_worktree", "Delete worktree"),
        ("p", "create_pr", "Create PR")
    ]

    selected_worktree = reactive("")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        yield MetadataDisplay("Select a worktree to view its metadata.", id="body")
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one(Sidebar).border_title = "Worktrees"
        self.theme = "tokyo-night"
        # Clean up orphaned worktrees on startup
        self.cleanup_orphaned_worktrees()

    def action_new_worktree(self) -> None:
        """An action to create a new worktree."""
        self.push_screen(WorktreeFormScreen(), self.handle_worktree_creation)

    def action_delete_worktree(self) -> None:
        """An action to delete the selected worktree."""
        if not self.selected_worktree:
            self.notify("No worktree selected", severity="warning")
            return

        self.push_screen(ConfirmDeleteScreen(self.selected_worktree), self.handle_worktree_deletion)

    def action_create_pr(self) -> None:
        """An action to create a pull request for the selected worktree."""
        if not self.selected_worktree:
            self.notify("No worktree selected", severity="warning")
            return

        self.push_screen(PRFormScreen(), self.handle_pr_submission)

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
            pr_worktrees = get_worktree_pr_status()

            if directories:
                for directory in directories:
                    icon = "●" if directory in sessions else "○"
                    pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                    sidebar.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
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

    def handle_pr_submission(self, form_data: dict[str, str | list[str]] | None) -> None:
        """Handle the result from the PR submission form."""
        if form_data is None:
            return  # User cancelled

        pr_title = str(form_data["title"])
        reviewers_raw = form_data.get("reviewers", [])
        reviewers: list[str] = reviewers_raw if isinstance(reviewers_raw, list) else []

        if not self.selected_worktree:
            self.notify("No worktree selected", severity="error")
            return

        # Find the worktree root directory
        current_path = Path.cwd()
        worktree_root = None

        if (current_path / ".bare").is_dir():
            worktree_root = current_path
        elif (current_path.parent / ".bare").is_dir():
            worktree_root = current_path.parent

        if worktree_root is None:
            self.notify("Could not find worktree root directory", severity="error")
            return

        worktree_path = worktree_root / self.selected_worktree
        if not worktree_path.exists():
            self.notify(f"Worktree directory not found: {self.selected_worktree}", severity="error")
            return

        try:
            # Get the current branch name
            branch_result = subprocess.run(
                ['git', '-C', str(worktree_path), 'branch', '--show-current'],
                capture_output=True,
                text=True,
                check=False
            )

            if branch_result.returncode != 0:
                self.notify("Failed to get current branch name", severity="error")
                return

            branch_name = branch_result.stdout.strip()
            if not branch_name:
                self.notify("No current branch found", severity="error")
                return

            # Push the branch to origin
            push_result = subprocess.run(
                ['git', '-C', str(worktree_path), 'push', '-u', 'origin', branch_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if push_result.returncode != 0:
                self.notify(f"Failed to push branch: {push_result.stderr}", severity="error")
                return

            # Prepare the gh pr create command
            pr_body_file = worktree_root / ".grove" / "metadata" / self.selected_worktree / "pr.md"

            gh_command: list[str] = ['gh', '-R', '.', 'pr', 'create', '--title', pr_title]

            # Add body file if it exists
            if pr_body_file.exists():
                gh_command.extend(['--body-file', str(pr_body_file)])
            else:
                gh_command.extend(['--body', ''])

            # Add reviewers if any selected
            if reviewers:
                gh_command.extend(['--reviewer', ','.join(reviewers)])

            # Run gh pr create from the worktree directory
            pr_result = subprocess.run(
                gh_command,
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            if pr_result.returncode != 0:
                self.notify(f"Failed to create PR: {pr_result.stderr}", severity="error")
                return

            # Extract PR URL from output (usually the last line)
            pr_output = pr_result.stdout.strip()
            pr_url = None

            # gh pr create outputs the URL on the last line
            if pr_output:
                lines = pr_output.split('\n')
                for line in reversed(lines):
                    if 'github.com' in line and '/pull/' in line:
                        pr_url = line.strip()
                        break

            # Write WORKTREE_PR_PUBLISHED=true to .env file in worktree dir
            env_file_path = worktree_path / ".env"
            try:
                # Read existing .env content if it exists
                existing_content = ""
                if env_file_path.exists():
                    existing_content = env_file_path.read_text()
                    # Check if WORKTREE_PR_PUBLISHED already exists
                    lines = existing_content.strip().split('\n')
                    updated = False
                    for i, line in enumerate(lines):
                        if line.startswith('WORKTREE_PR_PUBLISHED='):
                            lines[i] = 'WORKTREE_PR_PUBLISHED=true'
                            updated = True
                            break

                    if not updated:
                        lines.append('WORKTREE_PR_PUBLISHED=true')

                    new_content = '\n'.join(lines) + '\n'
                else:
                    new_content = 'WORKTREE_PR_PUBLISHED=true\n'

                env_file_path.write_text(new_content)
            except Exception as e:
                self.notify(f"Warning: Could not write to .env file: {str(e)}", severity="warning")

            # Open the PR URL if found
            if pr_url:
                try:
                    # Use the open command on macOS
                    subprocess.run(['open', pr_url], check=False)
                except Exception:
                    self.notify(f"PR created: {pr_url}", severity="information")
            else:
                self.notify("Pull request created successfully", severity="information")

            # Exit the app
            self.exit()

        except subprocess.TimeoutExpired:
            self.notify("Command timed out", severity="error")
        except FileNotFoundError as e:
            self.notify(f"Command not found: {e.filename}. Make sure 'gh' CLI is installed.", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")

    def on_list_view_highlighted(self, message: ListView.Highlighted) -> None:
        """Handle when a worktree is highlighted in the sidebar."""
        if message.item and message.item.query(Label):
            label = message.item.query_one(Label)
            # Extract worktree name from label text (remove icon and PR indicator)
            # Format is: "{icon}{pr_indicator} {directory}"
            # where icon is "●" or "○" and pr_indicator is " [bold]PR[/bold]" or ""
            # In Textual, Label stores its text in the renderable attribute
            label_text = label.renderable if isinstance(label.renderable, str) else str(label.renderable)

            # Remove the icon (first character) and any PR indicator
            if " " in label_text:
                # Find the last space, everything after it is the worktree name
                parts = label_text.split()
                # The worktree name is always the last part after all prefixes
                worktree_name = parts[-1] if parts else ""
                # Handle case where worktree name might have spaces (need to get everything after prefixes)
                # Look for the pattern: icon, optional PR indicator, then the actual name
                if "[bold]PR[/bold]" in label_text:
                    # If there's a PR indicator, split after it
                    after_pr = label_text.split("[/bold]")[-1].strip()
                    worktree_name = after_pr
                else:
                    # No PR indicator, just split after the icon
                    worktree_name = label_text.split(" ", 1)[1] if " " in label_text else ""

                self.selected_worktree = worktree_name

    def on_list_view_selected(self, message: ListView.Selected) -> None:
        """Handle when a worktree is selected (Enter pressed) in the sidebar."""
        if not self.selected_worktree:
            return

        # Find the worktree root directory
        current_path = Path.cwd()
        worktree_root = None

        if (current_path / ".bare").is_dir():
            worktree_root = current_path
        elif (current_path.parent / ".bare").is_dir():
            worktree_root = current_path.parent

        if worktree_root is None:
            self.notify("Could not find worktree root directory", severity="error")
            return

        # Construct the full path to the worktree
        worktree_path = worktree_root / self.selected_worktree

        if not worktree_path.exists():
            self.notify(f"Worktree directory not found: {self.selected_worktree}", severity="error")
            return

        try:
            # Run tmux-sessionizer command to switch to the session
            result = subprocess.run(
                ["tmux-sessionizer", str(worktree_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Success - exit the application
                self.exit()
            else:
                self.notify(f"Failed to switch to tmux session: {result.stderr}", severity="error")

        except subprocess.TimeoutExpired:
            self.notify("Command timed out", severity="error")
        except FileNotFoundError:
            self.notify("tmux-sessionizer command not found", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")

    def watch_selected_worktree(self, selected_worktree: str) -> None:
        """Update metadata display when selected worktree changes."""
        metadata_display = self.query_one("#body", MetadataDisplay)
        metadata_display.update_content(selected_worktree)

    def cleanup_orphaned_worktrees(self) -> None:
        """Clean up worktrees that have published PRs but no remote branch."""
        current_path = Path.cwd()
        bare_parent: Path | None = None

        # Find where the .bare directory is located
        if (current_path / ".bare").is_dir():
            bare_parent = current_path
        elif (current_path.parent / ".bare").is_dir():
            bare_parent = current_path.parent

        if bare_parent is None:
            return

        # Get worktrees with published PRs
        pr_worktrees = get_worktree_pr_status()
        if not pr_worktrees:
            return

        orphaned_worktrees: list[str] = []

        for worktree_name in pr_worktrees:
            worktree_path = bare_parent / worktree_name
            if not worktree_path.exists():
                continue

            # Check if the remote branch still exists
            if not check_remote_branch_exists(worktree_path):
                orphaned_worktrees.append(worktree_name)

        if not orphaned_worktrees:
            return

        # Clean up orphaned worktrees
        for worktree_name in orphaned_worktrees:
            # Extract prefix from worktree name
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

                if result.returncode == 0:
                    # Check if there's a tmux session with the same name and kill it
                    try:
                        session_check = subprocess.run(
                            ['tmux', 'has-session', '-t', worktree_name],
                            capture_output=True,
                            text=True,
                            check=False
                        )

                        if session_check.returncode == 0:
                            subprocess.run(
                                ['tmux', 'kill-session', '-t', worktree_name],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                    except (FileNotFoundError, subprocess.SubprocessError):
                        pass

                    self.notify(f"Auto-cleaned orphaned worktree: {worktree_name}", severity="information")
                else:
                    self.notify(f"Failed to auto-clean worktree {worktree_name}: {result.stderr}", severity="warning")

            except subprocess.TimeoutExpired:
                self.notify(f"Timeout cleaning worktree: {worktree_name}", severity="warning")
            except FileNotFoundError:
                self.notify("worktree-manager command not found", severity="warning")
            except Exception as e:
                self.notify(f"Error cleaning worktree {worktree_name}: {str(e)}", severity="warning")

        # Refresh the sidebar after cleanup
        if orphaned_worktrees:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.clear()
            directories = get_worktree_directories()
            sessions = get_active_tmux_sessions()
            pr_worktrees = get_worktree_pr_status()

            if directories:
                for directory in directories:
                    icon = "●" if directory in sessions else "○"
                    pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                    sidebar.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
            else:
                sidebar.append(ListItem(Label("No directories found")))


def main() -> None:
    """Main entry point for Grove application."""
    if not is_bare_git_repository():
        print("Error: Grove must be run from a bare git repository (directory containing '.bare' subdirectory)", file=sys.stderr)
        sys.exit(1)

    app = GroveApp()
    app.run()


if __name__ == "__main__":
    main()
