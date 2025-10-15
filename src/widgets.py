"""Textual widgets for Grove application."""

from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Markdown
from textual.widget import Widget
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text
from rich.console import RenderableType

from .utils import get_worktree_directories, get_active_tmux_sessions, get_worktree_pr_status
from .utils import get_worktree_metadata, get_worktree_git_info, get_worktree_git_status


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

        # Title
        title = Text("Git Status", style="bold")
        lines.append(title)
        lines.append(Text())  # Empty line

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