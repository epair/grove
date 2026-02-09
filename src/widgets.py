"""Textual widgets for Grove application."""

from typing import Any
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label, Markdown, Static
from textual.widget import Widget
from textual.binding import Binding
from textual.reactive import reactive
from textual.containers import VerticalScroll, Horizontal
from rich.text import Text
from rich.console import RenderableType

from .config import ConfigError
from .utils import (
    get_worktree_directories,
    get_active_tmux_sessions,
    get_worktree_pr_status,
    get_worktree_metadata,
    get_worktree_git_info,
    get_worktree_git_status,
    get_tmux_pane_preview,
    get_worktree_git_log,
)


class Sidebar(ListView):
    BINDINGS = [
        Binding("j", "cursor_down", "Move down", show=False),
        Binding("k", "cursor_up", "Move up", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose initial empty structure - data loaded on mount."""
        yield ListItem(Label("Loading..."))

    def on_mount(self) -> None:
        """Load worktree data when widget is mounted."""
        self.refresh_directories()

    def refresh_directories(self) -> None:
        """Refresh the sidebar with current worktree directories."""
        try:
            directories = get_worktree_directories()
            sessions = get_active_tmux_sessions()
            pr_worktrees = get_worktree_pr_status()

            self.clear()

            if directories:
                for directory in directories:
                    icon = "●" if directory in sessions else "○"
                    pr_indicator = " [bold]PR[/bold]" if directory in pr_worktrees else ""
                    self.append(ListItem(Label(f"{icon}{pr_indicator} {directory}")))
            else:
                self.append(ListItem(Label("No directories found")))
        except ConfigError as e:
            self.clear()
            self.append(ListItem(Label(f"[bold red]Error:[/bold red] {str(e)}")))
            self.append(ListItem(Label("[dim]Check your Grove configuration[/dim]")))


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

    # Section definitions: (status_key, header, icon, color)
    _SECTIONS: list[tuple[str, str, str, str]] = [
        ("unstaged", "Unstaged Changes", "● ", "red"),
        ("staged", "Staged Changes", "✓ ", "green"),
        ("untracked", "Untracked Files", "? ", "yellow"),
    ]

    def update_content(self, worktree_name: str) -> None:
        """Update the display with git status for the given worktree."""
        self.worktree_name = worktree_name
        self.refresh(layout=True)

    def _render_file_section(self, files: list[str], header: str, icon: str, color: str) -> list[Text]:
        """Render a section of files (staged, unstaged, or untracked) with consistent styling."""
        lines: list[Text] = []
        lines.append(Text(header, style=f"bold {color}"))
        for file in files:
            file_line = Text()
            file_line.append(icon, style=f"bold {color}")
            file_line.append(file, style=color)
            lines.append(file_line)
        return lines

    def render(self) -> RenderableType:
        """Render git status with Rich Text styling."""
        if not self.worktree_name:
            return Text("Select a worktree to view git status", style="dim italic")

        status = get_worktree_git_status(self.worktree_name)

        if not status["staged"] and not status["unstaged"] and not status["untracked"]:
            return Text("Working tree clean", style="dim italic")

        lines: list[Text] = []
        for key, header, icon, color in self._SECTIONS:
            if status[key]:
                if lines:
                    lines.append(Text())  # Separator between sections
                lines.extend(self._render_file_section(status[key], header, icon, color))

        return Text("\n").join(lines)


# Sync status display configuration: (icon, label_template, color)
_SYNC_STATUS_CONFIG: dict[str, tuple[str, str, str]] = {
    "up-to-date": ("✓ ", "Up to date", "green"),
    "ahead": ("↑ ", "Ahead {ahead} commit{s}", "yellow"),
    "behind": ("↓ ", "Behind {behind} commit{s}", "red"),
    "diverged": ("⚠ ", "Diverged (↑{ahead} ↓{behind})", "magenta"),
}


class GitLogDisplay(Widget):
    """Widget to display git log with lazygit-style formatting (pushed vs unpushed commits)."""

    worktree_name: reactive[str] = reactive("")

    def update_content(self, worktree_name: str) -> None:
        """Update the display with git log for the given worktree."""
        self.worktree_name = worktree_name
        self.refresh(layout=True)

    def _render_sync_status(self, log_data: dict[str, Any]) -> Text:
        """Render the sync status line from log data."""
        sync_status = log_data["sync_status"]
        comparison_branch = log_data.get("comparison_branch", "")

        if sync_status == "no-upstream":
            line = Text()
            line.append("• ", style="dim")
            line.append("No comparison branch available", style="dim italic")
            return line

        config = _SYNC_STATUS_CONFIG.get(sync_status)
        if not config:
            return Text()

        icon, label_template, color = config
        ahead = log_data["ahead_count"]
        behind = log_data["behind_count"]

        label = label_template.format(
            ahead=ahead,
            behind=behind,
            s="s" if (ahead > 1 if "ahead" in label_template.lower() else behind > 1) else "",
        )

        line = Text()
        line.append(icon, style=f"bold {color}")
        line.append(label, style=color)
        if comparison_branch:
            line.append(f" ({comparison_branch})", style=f"dim {color}")
        return line

    def _render_commit(self, commit: dict[str, Any]) -> list[Text]:
        """Render a single commit entry (hash + message line, then author + date line)."""
        if not commit["is_pushed"]:
            hash_style, message_style = "bold yellow", "bold white"
            author_style, date_style = "cyan", "green"
        else:
            hash_style, message_style = "dim cyan", "dim white"
            author_style, date_style = "dim", "dim"

        commit_line = Text()
        commit_line.append(f"{commit['hash']} ", style=hash_style)
        commit_line.append(f"{commit['message']}", style=message_style)

        info_line = Text()
        info_line.append("  ", style="")
        info_line.append(f"{commit['author']}", style=author_style)
        info_line.append(" • ", style="dim")
        info_line.append(f"{commit['date']}", style=date_style)

        return [commit_line, info_line]

    def render(self) -> RenderableType:
        """Render git log with Rich Text styling."""
        if not self.worktree_name:
            return Text("Select a worktree to view git log", style="dim italic")

        log_data = get_worktree_git_log(self.worktree_name)
        lines: list[Text] = [self._render_sync_status(log_data), Text()]

        commits = log_data["commits"]
        if not commits:
            lines.append(Text("No commits", style="dim italic"))
        else:
            for commit in commits:
                lines.extend(self._render_commit(commit))

        return Text("\n").join(lines)


class MetadataTopDisplay(Markdown):
    """Widget to display description and PR info metadata."""

    @staticmethod
    def _format_section(heading: str, content: str | None, fallback: str) -> list[str]:
        """Format a markdown section with heading and content or fallback text."""
        return [f"## {heading}", content if content else f"*{fallback}*", ""]

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        if not worktree_name:
            self.update("*Select a worktree to view metadata*")
            return

        metadata = get_worktree_metadata(worktree_name)

        content_parts: list[str] = []
        content_parts.extend(self._format_section(
            "Description", metadata.get("description"), "No description available"
        ))
        content_parts.extend(self._format_section(
            "Pull Request Info", metadata.get("pr"), "No PR information available"
        ))

        self.update("\n".join(content_parts))


class MetadataBottomDisplay(Markdown):
    """Widget to display notes and git information."""

    @staticmethod
    def _format_section(heading: str, content: str | None, fallback: str) -> list[str]:
        """Format a markdown section with heading and content or fallback text."""
        return [f"## {heading}", content if content else f"*{fallback}*", ""]

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        if not worktree_name:
            self.update("*Select a worktree to view metadata*")
            return

        metadata = get_worktree_metadata(worktree_name)
        git_info = get_worktree_git_info(worktree_name)

        content_parts: list[str] = []
        content_parts.extend(self._format_section(
            "Notes", metadata.get("notes"), "No notes available"
        ))
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
        window_index = self.window_data.get("window_index", "?")
        window_name = self.window_data.get("window_name", "unknown")
        is_active = self.window_data.get("is_active", False)

        active_indicator = "*" if is_active else " "
        title = f"{active_indicator}{window_index}: {window_name}"

        yield Static(title, classes="window-title")
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
        container = self.query_one("#windows-container", Horizontal)
        container.remove_children()

        if not worktree_name:
            container.mount(Static("Select a worktree to view tmux pane preview", classes="preview-placeholder"))
            return

        preview_data = get_tmux_pane_preview(worktree_name)

        # String response means a status/error message
        if isinstance(preview_data, str):
            css_class = "preview-error" if preview_data.startswith("Error capturing pane:") else "preview-placeholder"
            container.mount(Static(preview_data, classes=css_class))
            return

        # List of window data dicts
        for window_data in preview_data:
            container.mount(WindowPreview(window_data))


class MetadataDisplay(VerticalScroll):
    """Widget to display pr.md metadata file."""

    can_focus = True

    BINDINGS = [
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the markdown display."""
        yield Markdown("*Select a worktree to view PR description*", id="metadata_markdown")

    def update_content(self, worktree_name: str) -> None:
        """Update the display with metadata for the given worktree."""
        markdown = self.query_one("#metadata_markdown", Markdown)

        if not worktree_name:
            markdown.update("*Select a worktree to view PR description*")
            return

        metadata = get_worktree_metadata(worktree_name)

        if metadata:
            markdown.update(metadata)
        else:
            markdown.update("*No PR description available*")
