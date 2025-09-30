"""Textual widgets for Grove application."""

from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Markdown
from textual.binding import Binding

from .utils import get_worktree_directories, get_active_tmux_sessions, get_worktree_pr_status
from .utils import get_worktree_metadata, get_worktree_git_info


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