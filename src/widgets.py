"""Textual widgets for Grove application."""

from typing import Any
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Markdown, Static
from textual.widget import Widget
from textual.binding import Binding
from textual.reactive import reactive
from textual.containers import VerticalScroll, Horizontal, Vertical
from rich.text import Text
from rich.console import RenderableType

from .utils import get_worktree_directories, get_active_tmux_sessions, get_worktree_pr_status
from .utils import get_worktree_metadata, get_worktree_git_info, get_worktree_git_status
from .utils import get_tmux_pane_preview, get_worktree_git_log


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


class ScrollableContainer(VerticalScroll):
    """A focusable scrollable container with j/k navigation."""

    BINDINGS = [
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
    ]

    can_focus = True

    def action_scroll_down(self) -> None:
        """Scroll down one line."""
        self.scroll_down(animate=False)

    def action_scroll_up(self) -> None:
        """Scroll up one line."""
        self.scroll_up(animate=False)


class GitStatusDisplay(Widget):
    """Widget to display git status (staged, unstaged, untracked files) with lazygit-style formatting."""

    worktree_name: reactive[str] = reactive("")

    def update_content(self, worktree_name: str) -> None:
        """Update the display with git status for the given worktree."""
        self.worktree_name = worktree_name
        self.refresh(layout=True)  # Force layout recalculation for proper height adjustment

    def render(self) -> RenderableType:
        """Render git status with Rich Text styling."""
        if not self.worktree_name:
            return Text("Select a worktree to view git status", style="dim italic")

        # Get git status
        status = get_worktree_git_status(self.worktree_name)

        # Build the output with Rich Text
        lines: list[Text] = []

        # Check if working tree is clean
        if not status["staged"] and not status["unstaged"] and not status["untracked"]:
            lines.append(Text("Working tree clean", style="dim italic"))
            return Text("\n").join(lines)

        # Add unstaged files (show first, like lazygit)
        if status["unstaged"]:
            lines.append(Text("Unstaged Changes", style="bold red"))
            for file in status["unstaged"]:
                # Use red for unstaged files with a dot icon
                file_line = Text()
                file_line.append("● ", style="bold red")
                file_line.append(file, style="red")
                lines.append(file_line)
            lines.append(Text())  # Empty line

        # Add staged files
        if status["staged"]:
            lines.append(Text("Staged Changes", style="bold green"))
            for file in status["staged"]:
                # Use green for staged files with a checkmark icon
                file_line = Text()
                file_line.append("✓ ", style="bold green")
                file_line.append(file, style="green")
                lines.append(file_line)
            lines.append(Text())  # Empty line

        # Add untracked files
        if status["untracked"]:
            lines.append(Text("Untracked Files", style="bold yellow"))
            for file in status["untracked"]:
                # Use yellow/dim for untracked files with a question mark icon
                file_line = Text()
                file_line.append("? ", style="bold yellow")
                file_line.append(file, style="yellow")
                lines.append(file_line)

        return Text("\n").join(lines)


class GitLogDisplay(Widget):
    """Widget to display git log with lazygit-style formatting (pushed vs unpushed commits)."""

    worktree_name: reactive[str] = reactive("")

    def update_content(self, worktree_name: str) -> None:
        """Update the display with git log for the given worktree."""
        self.worktree_name = worktree_name
        self.refresh(layout=True)  # Force layout recalculation for proper height adjustment

    def render(self) -> RenderableType:
        """Render git log with Rich Text styling."""
        if not self.worktree_name:
            return Text("Select a worktree to view git log", style="dim italic")

        # Get git log data
        log_data = get_worktree_git_log(self.worktree_name)

        # Build the output with Rich Text
        lines: list[Text] = []

        # Show sync status at the top
        sync_status = log_data["sync_status"]
        ahead_count = log_data["ahead_count"]
        behind_count = log_data["behind_count"]
        comparison_branch = log_data.get("comparison_branch", "")

        if sync_status == "up-to-date":
            status_line = Text()
            status_line.append("✓ ", style="bold green")
            status_line.append("Up to date", style="green")
            if comparison_branch:
                status_line.append(f" ({comparison_branch})", style="dim green")
            lines.append(status_line)
        elif sync_status == "ahead":
            status_line = Text()
            status_line.append("↑ ", style="bold yellow")
            status_line.append(f"Ahead {ahead_count} commit{'s' if ahead_count > 1 else ''}", style="yellow")
            if comparison_branch:
                status_line.append(f" ({comparison_branch})", style="dim yellow")
            lines.append(status_line)
        elif sync_status == "behind":
            status_line = Text()
            status_line.append("↓ ", style="bold red")
            status_line.append(f"Behind {behind_count} commit{'s' if behind_count > 1 else ''}", style="red")
            if comparison_branch:
                status_line.append(f" ({comparison_branch})", style="dim red")
            lines.append(status_line)
        elif sync_status == "diverged":
            status_line = Text()
            status_line.append("⚠ ", style="bold magenta")
            status_line.append(f"Diverged (↑{ahead_count} ↓{behind_count})", style="magenta")
            if comparison_branch:
                status_line.append(f" ({comparison_branch})", style="dim magenta")
            lines.append(status_line)
        elif sync_status == "no-upstream":
            status_line = Text()
            status_line.append("• ", style="dim")
            status_line.append("No comparison branch available", style="dim italic")
            lines.append(status_line)

        lines.append(Text())  # Empty line

        # Show commits
        commits = log_data["commits"]

        if not commits:
            lines.append(Text("No commits", style="dim italic"))
        else:
            for commit in commits:
                # Determine style based on whether commit is already in upstream/main
                # is_pushed means: already in upstream branch OR already in main branch
                if not commit["is_pushed"]:
                    # New commits (not in upstream or main) - bright/yellow style
                    hash_style = "bold yellow"
                    message_style = "bold white"
                    author_style = "cyan"
                    date_style = "green"
                else:
                    # Existing commits (in upstream or main) - dim/gray style like in lazygit
                    hash_style = "dim cyan"
                    message_style = "dim white"
                    author_style = "dim"
                    date_style = "dim"

                # Build commit line: hash message (author, date)
                commit_line = Text()
                commit_line.append(f"{commit['hash']} ", style=hash_style)
                commit_line.append(f"{commit['message']}", style=message_style)
                lines.append(commit_line)

                # Add author and date on next line with indent
                info_line = Text()
                info_line.append("  ", style="")
                info_line.append(f"{commit['author']}", style=author_style)
                info_line.append(" • ", style="dim")
                info_line.append(f"{commit['date']}", style=date_style)
                lines.append(info_line)

        return Text("\n").join(lines)


class MetadataTopDisplay(Markdown):
    """Widget to display description and PR info metadata."""

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        if not worktree_name:
            self.update("*Select a worktree to view metadata*")
            return

        # Get metadata
        metadata = get_worktree_metadata(worktree_name)

        # Format the content
        content_parts = []

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

        self.update("\n".join(content_parts))


class MetadataBottomDisplay(Markdown):
    """Widget to display notes and git information."""

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        if not worktree_name:
            self.update("*Select a worktree to view metadata*")
            return

        # Get metadata and git info
        metadata = get_worktree_metadata(worktree_name)
        git_info = get_worktree_git_info(worktree_name)

        # Format the content
        content_parts = []

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


class WindowPreview(Widget):
    """Widget to display a single tmux window's pane content."""

    def __init__(self, window_data: dict[str, str | bool], **kwargs: Any) -> None:
        """Initialize with window data."""
        super().__init__(**kwargs)
        self.window_data = window_data

    def compose(self) -> ComposeResult:
        """Compose the window preview with title and content."""
        # Window title with index and name
        window_index = self.window_data.get("window_index", "?")
        window_name = self.window_data.get("window_name", "unknown")
        is_active = self.window_data.get("is_active", False)

        # Add an asterisk to indicate the active window
        active_indicator = "*" if is_active else " "
        title = f"{active_indicator}{window_index}: {window_name}"

        yield Static(title, classes="window-title")
        # Get content as string (we know it's always a string in our data structure)
        content = str(self.window_data.get("content", ""))
        yield WindowContent(content, classes="window-content")


class WindowContent(Widget):
    """Widget to render window pane content."""

    def __init__(self, content: str, **kwargs: Any) -> None:
        """Initialize with content."""
        super().__init__(**kwargs)
        self.content = content

    def render(self) -> RenderableType:
        """Render the window content."""
        return Text(self.content, style="white on default", no_wrap=False, overflow="fold")


class TmuxPanePreview(Widget):
    """Widget to display live tmux pane preview content for all windows."""

    worktree_name: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        """Compose the initial empty state."""
        yield Horizontal(id="windows-container")

    def update_content(self, worktree_name: str) -> None:
        """Update the display with pane preview for the given worktree."""
        self.worktree_name = worktree_name

    def watch_worktree_name(self, worktree_name: str) -> None:
        """React to worktree name changes and rebuild the windows display."""
        # Get the container
        container = self.query_one("#windows-container", Horizontal)

        # Clear existing windows
        container.remove_children()

        if not worktree_name:
            # Show placeholder message
            placeholder = Static("Select a worktree to view tmux pane preview", classes="preview-placeholder")
            container.mount(placeholder)
            return

        # Get pane preview data
        preview_data = get_tmux_pane_preview(worktree_name)

        # Check if we got an error message string
        if isinstance(preview_data, str):
            # Show error/status message
            if preview_data in ["Tmux not available", "No active tmux session", "No windows in session", "Empty pane"]:
                placeholder = Static(preview_data, classes="preview-placeholder")
            elif preview_data.startswith("Error capturing pane:"):
                placeholder = Static(preview_data, classes="preview-error")
            else:
                placeholder = Static(preview_data, classes="preview-placeholder")

            container.mount(placeholder)
            return

        # We have window data - create a preview for each window
        if preview_data:
            for window_data in preview_data:
                window_preview = WindowPreview(window_data)
                container.mount(window_preview)