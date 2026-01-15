"""Main Grove application."""

import subprocess
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, ListView, ListItem, Label
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal

from .widgets import Sidebar, ScrollableContainer, GitStatusDisplay, GitLogDisplay, TmuxPanePreview, MetadataDisplay
from .screens import WorktreeFormScreen, ConfirmDeleteScreen, PRFormScreen
from .config import get_repo_path
from .utils import (
    get_worktree_directories,
    get_active_tmux_sessions,
    get_worktree_pr_status,
    check_remote_branch_exists,
    create_worktree_with_branch,
    remove_worktree_with_branch,
    create_or_switch_to_session,
    get_tmux_server,
    session_exists,
    is_inside_tmux,
)


class GroveApp(App):
    """A Textual app to manage git worktrees."""

    CSS_PATH = "../app.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_worktree", "New worktree"),
        ("d", "delete_worktree", "Delete worktree"),
        ("p", "create_pr", "Create PR"),
        ("e", "edit_metadata", "Edit metadata"),
        ("ctrl+r", "switch_repository", "Switch Repository"),
    ]

    selected_worktree = reactive("")

    def __init__(self) -> None:
        """Initialize the Grove app."""
        super().__init__()
        self.restart_with_different_repo = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Sidebar(id='sidebar')
        with Vertical(id='body'):
            with ScrollableContainer(id='metadata_container'):
                yield MetadataDisplay(id="metadata")
            with Horizontal(id='git_status_row'):
                with ScrollableContainer(id='git_status_container'):
                    yield GitStatusDisplay(id="git_status")
                with ScrollableContainer(id='git_log_container'):
                    yield GitLogDisplay(id="git_log")
            with ScrollableContainer(id='metadata_bottom_container'):
                yield TmuxPanePreview(id="tmux_preview")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Sidebar).border_title = "Worktrees"
        self.query_one("#metadata_container").border_title = "PR Description"
        self.query_one("#git_status_container").border_title = "Git Status"
        self.query_one("#git_log_container").border_title = "Git Log"
        self.query_one("#metadata_bottom_container").border_title = "Tmux Pane Preview"
        self.theme = "tokyo-night"
        # Clean up orphaned worktrees on startup
        self.cleanup_orphaned_worktrees()
        # Auto-select the current worktree
        self.auto_select_current_worktree()

    def detect_current_worktree(self) -> str | None:
        """Detect which worktree the user was in when launching Grove.

        Returns:
            The worktree name if detected, None otherwise.
        """
        current_path = Path.cwd()
        bare_parent = get_repo_path()

        # Get list of valid worktrees
        worktrees = get_worktree_directories()
        if not worktrees:
            return None

        # Check if current path is within bare_parent
        try:
            relative_path = current_path.relative_to(bare_parent)
        except ValueError:
            # current_path is not under bare_parent
            return None

        # Get the first component of the relative path
        parts = relative_path.parts
        if not parts:
            # We're exactly at bare_parent - default to first worktree
            return worktrees[0]

        first_dir = parts[0]

        # Check if this directory is a valid worktree
        if first_dir in worktrees:
            return first_dir

        # Not in a worktree (e.g., in .grove, .bare, or other hidden dir)
        # Default to first worktree
        return worktrees[0]

    def auto_select_current_worktree(self) -> None:
        """Auto-select and highlight the worktree the user was in when launching."""
        detected_worktree = self.detect_current_worktree()

        if detected_worktree is None:
            return

        # Get the sidebar and list of worktrees
        sidebar = self.query_one("#sidebar", Sidebar)
        worktrees = get_worktree_directories()

        # Find the index of the detected worktree
        try:
            index = worktrees.index(detected_worktree)
        except ValueError:
            # Worktree not in list (shouldn't happen, but defensive)
            return

        # Set the sidebar index to select the worktree
        # This will trigger on_list_view_highlighted which updates selected_worktree
        sidebar.index = index

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

    def action_edit_metadata(self) -> None:
        """An action to edit pr.md metadata file in neovim."""
        if not self.selected_worktree:
            self.notify("No worktree selected", severity="warning")
            return

        # Get worktree root directory
        worktree_root = get_repo_path()

        # Construct metadata file path
        metadata_dir = worktree_root / ".grove" / "metadata" / self.selected_worktree
        metadata_file = metadata_dir / "pr.md"

        # Ensure metadata directory exists
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Ensure metadata file exists (create with template if needed)
        if not metadata_file.exists():
            metadata_file.write_text("# Pull Request\n\nWhat are you building?\n\n")

        # Get tmux server
        server = get_tmux_server()
        if server is None:
            self.notify("Could not connect to tmux server", severity="error")
            return

        # Get or create session
        session_name = self.selected_worktree.replace('.', '-')
        worktree_path = worktree_root / self.selected_worktree

        if not session_exists(server, session_name):
            # Create session
            try:
                session = server.new_session(
                    session_name=session_name,
                    start_directory=str(worktree_path),
                    attach=False
                )
            except Exception as e:
                self.notify(f"Failed to create tmux session: {str(e)}", severity="error")
                return
        else:
            # Get existing session
            sessions = server.sessions.filter(session_name=session_name)
            if not sessions:
                self.notify(f"Session '{session_name}' not found", severity="error")
                return
            session = sessions[0]

        # Create new window in session
        try:
            new_window = session.new_window(
                window_name="edit-pr",
                start_directory=str(worktree_path),
                attach=False
            )

            # Open neovim in the new window (exit when neovim closes)
            new_window.panes[0].send_keys(f"nvim {metadata_file}; exit")

            # Select the new window (make it active)
            new_window.select_window()

            # Switch to the session
            if is_inside_tmux():
                session.switch_client()
            else:
                session.attach()

            # Exit the app
            self.exit()

        except Exception as e:
            self.notify(f"Failed to open file in tmux: {str(e)}", severity="error")

    def handle_worktree_creation(self, form_data: dict[str, str] | None) -> None:
        """Handle the result from the worktree creation form."""
        if form_data is None:
            return  # User cancelled

        prefix = form_data["prefix"]
        name = form_data["name"]

        try:
            # Create worktree using GitPython
            success, error_msg = create_worktree_with_branch(name, prefix)

            if not success:
                self.notify(f"Failed to create worktree: {error_msg}", severity="error")
                return

            # Wait a moment for the worktree to be created
            time.sleep(0.5)

            # Get the worktree root directory
            worktree_root = get_repo_path()

            # Create or switch to tmux session
            worktree_path = worktree_root / name
            success, error_msg = create_or_switch_to_session(worktree_path)

            if success:
                # Success - exit the application
                self.exit()
            else:
                self.notify(f"Worktree created but failed to start tmux session: {error_msg}", severity="warning")

        except Exception as e:
            self.notify(f"Unexpected error: {str(e)}", severity="error")

    def handle_worktree_deletion(self, confirmed: bool | None) -> None:
        """Handle the result from the worktree deletion confirmation."""
        if confirmed is None or not confirmed:
            return  # User cancelled

        worktree_name = self.selected_worktree
        if not worktree_name:
            return

        try:
            # Remove worktree using GitPython (will query git for the branch name)
            success, error_msg = remove_worktree_with_branch(worktree_name)

            if not success:
                self.notify(f"Failed to delete worktree: {error_msg}", severity="error")
                return

            # Check if there's a warning message (branch deletion, Docker cleanup, etc.)
            has_warning = bool(error_msg)

            # Check if there's a tmux session with the same name and kill it
            tmux_killed = False
            try:
                server = get_tmux_server()
                if server and session_exists(server, worktree_name):
                    # Session exists, kill it
                    try:
                        found_sessions = server.sessions.filter(session_name=worktree_name)
                        if found_sessions:
                            found_sessions[0].kill_session()
                            tmux_killed = True
                    except Exception:
                        if has_warning:
                            self.notify(f"{error_msg} Worktree deleted but failed to kill tmux session", severity="warning")
                        else:
                            self.notify('Worktree deleted but failed to kill tmux session', severity="warning")
                        # Refresh sidebar and return early
                        sidebar = self.query_one("#sidebar", Sidebar)
                        sidebar.clear()
                        directories = get_worktree_directories()
                        active_sessions = get_active_tmux_sessions()
                        pr_worktrees = get_worktree_pr_status()
                        if directories:
                            for directory in directories:
                                icon = "●" if directory in active_sessions else "○"
                                pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                                sidebar.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
                        else:
                            sidebar.append(ListItem(Label("No directories found")))
                        if self.selected_worktree == worktree_name:
                            self.selected_worktree = ""
                        return
            except Exception:
                # tmux not available or other error
                pass

            # Build success message
            if has_warning:
                self.notify(error_msg, severity="warning")
            else:
                success_msg = f"Worktree '{worktree_name}'"
                if tmux_killed:
                    success_msg += " and its tmux session"
                success_msg += " deleted successfully"
                self.notify(success_msg, severity="information")

            # Refresh the sidebar by recreating it
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.clear()
            directories = get_worktree_directories()
            active_sessions = get_active_tmux_sessions()
            pr_worktrees = get_worktree_pr_status()

            if directories:
                for directory in directories:
                    icon = "●" if directory in active_sessions else "○"
                    pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                    sidebar.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
            else:
                sidebar.append(ListItem(Label("No directories found")))

            # Clear selection if the deleted worktree was selected
            if self.selected_worktree == worktree_name:
                self.selected_worktree = ""

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
        worktree_root = get_repo_path()

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

            gh_command: list[str] = ['gh', 'pr', 'create', '--title', pr_title]

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
            # In Textual 6.0+, Label stores its text in the content property
            # The content can be various types, so we need to convert it to string
            label_text = str(label.content)

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

        # Get the worktree root directory
        worktree_root = get_repo_path()

        # Construct the full path to the worktree
        worktree_path = worktree_root / self.selected_worktree

        if not worktree_path.exists():
            self.notify(f"Worktree directory not found: {self.selected_worktree}", severity="error")
            return

        # Create or switch to tmux session
        success, error_msg = create_or_switch_to_session(worktree_path)

        if success:
            # Success - exit the application
            self.exit()
        else:
            self.notify(f"Failed to switch to tmux session: {error_msg}", severity="error")

    def watch_selected_worktree(self, selected_worktree: str) -> None:
        """Update all displays when selected worktree changes."""
        git_status = self.query_one("#git_status", GitStatusDisplay)
        git_log = self.query_one("#git_log", GitLogDisplay)
        metadata_display = self.query_one("#metadata", MetadataDisplay)
        tmux_preview = self.query_one("#tmux_preview", TmuxPanePreview)

        git_status.update_content(selected_worktree)
        git_log.update_content(selected_worktree)
        metadata_display.update_content(selected_worktree)
        tmux_preview.update_content(selected_worktree)

    def cleanup_orphaned_worktrees(self) -> None:
        """Clean up worktrees that have published PRs but no remote branch."""
        bare_parent = get_repo_path()

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
            try:
                # Remove worktree using GitPython (will query git for the branch name)
                success, error_msg = remove_worktree_with_branch(worktree_name)

                if success:
                    # Check if there's a tmux session with the same name and kill it
                    try:
                        server = get_tmux_server()
                        if server and session_exists(server, worktree_name):
                            found_sessions = server.sessions.filter(session_name=worktree_name)
                            if found_sessions:
                                found_sessions[0].kill_session()
                    except Exception:
                        pass

                    if error_msg:
                        self.notify(f"Auto-cleaned worktree {worktree_name}: {error_msg}", severity="warning")
                    else:
                        self.notify(f"Auto-cleaned orphaned worktree: {worktree_name}", severity="information")
                else:
                    self.notify(f"Failed to auto-clean worktree {worktree_name}: {error_msg}", severity="warning")

            except Exception as e:
                self.notify(f"Error cleaning worktree {worktree_name}: {str(e)}", severity="warning")

        # Refresh the sidebar after cleanup
        if orphaned_worktrees:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.clear()
            directories = get_worktree_directories()
            active_sessions = get_active_tmux_sessions()
            pr_worktrees = get_worktree_pr_status()

            if directories:
                for directory in directories:
                    icon = "●" if directory in active_sessions else "○"
                    pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                    sidebar.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
            else:
                sidebar.append(ListItem(Label("No directories found")))

    def action_switch_repository(self) -> None:
        """Show repository selection screen and restart with selected repo."""
        from .config import get_repositories
        from .screens import RepositorySelectionScreen

        repos = get_repositories()

        def handle_selection(selected_path: str | None) -> None:
            if selected_path:
                # User selected a different repo
                current_repo = get_repo_path()
                if Path(selected_path) != current_repo:
                    # Mark for restart
                    self.restart_with_different_repo = True
                    self.exit()
            # If None (cancelled) or same repo, do nothing

        self.push_screen(RepositorySelectionScreen(repos), handle_selection)
