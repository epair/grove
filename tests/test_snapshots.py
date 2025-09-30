"""Snapshot tests for Grove application screens."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src import GroveApp


class TestSnapshots:
    """Snapshot tests for all Grove screens."""

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_main_app_screen(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for the main GroveApp screen with sidebar and metadata display."""
        # Mock no cleanup, no tmux sessions, feature-one has PR
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()
        assert snap_compare(app, terminal_size=(120, 40))

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_main_app_screen_with_tmux_session(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for main screen with active tmux session."""
        # Mock with bugfix-01 having an active tmux session
        mock_cleanup.return_value = None
        mock_sessions.return_value = {'bugfix-01'}
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()
        assert snap_compare(app, terminal_size=(120, 40))

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_main_app_with_selected_worktree(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for main screen with a worktree selected and metadata displayed."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Select the first worktree before taking snapshot."""
            sidebar = app.query_one("#sidebar")
            sidebar.index = 0
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_worktree_form_screen(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for the WorktreeFormScreen modal."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Open the worktree creation form before taking snapshot."""
            await pilot.press("n")
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_worktree_form_screen_with_input(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for WorktreeFormScreen with user input."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Open form, enter some text, then take snapshot."""
            await pilot.press("n")
            await pilot.pause()
            # Focus is already on prefix input, type there
            await pilot.press(*list("custom-prefix/"))
            await pilot.pause()
            # Tab to name input
            await pilot.press("tab")
            await pilot.pause()
            # Type the name
            await pilot.press(*list("my-feature"))
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_confirm_delete_screen(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for the ConfirmDeleteScreen modal."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Select a worktree and open delete confirmation before taking snapshot."""
            sidebar = app.query_one("#sidebar")
            sidebar.index = 0
            await pilot.pause()
            # Press 'd' to open delete confirmation
            await pilot.press("d")
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_pr_form_screen(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for the PRFormScreen modal."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Select a worktree and open PR form before taking snapshot."""
            sidebar = app.query_one("#sidebar")
            sidebar.index = 0
            await pilot.pause()
            # Press 'p' to open PR form
            await pilot.press("p")
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)

    @patch('src.utils.get_active_tmux_sessions')
    @patch('src.utils.get_worktree_pr_status')
    @patch('src.app.GroveApp.cleanup_orphaned_worktrees')
    def test_pr_form_screen_with_input(
        self,
        mock_cleanup: Any,
        mock_pr_status: Any,
        mock_sessions: Any,
        snap_compare: Any,
        change_to_example_repo: Path
    ) -> None:
        """Snapshot test for PRFormScreen with user input and reviewer selections."""
        mock_cleanup.return_value = None
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}

        app = GroveApp()

        async def run_before(pilot: Any) -> None:
            """Open PR form, enter title, select reviewers, then take snapshot."""
            sidebar = app.query_one("#sidebar")
            sidebar.index = 0
            await pilot.pause()
            # Press 'p' to open PR form
            await pilot.press("p")
            await pilot.pause()
            # Type PR title
            await pilot.press(*list("Add new feature for user management"))
            await pilot.pause()
            # Tab down to reviewers and toggle some checkboxes
            await pilot.press("tab")
            await pilot.pause()
            # Toggle swlkr checkbox (second one)
            await pilot.press("down")
            await pilot.press("space")
            await pilot.pause()
            # Toggle daviswahl checkbox (third one)
            await pilot.press("down")
            await pilot.press("space")
            await pilot.pause()

        assert snap_compare(app, terminal_size=(120, 40), run_before=run_before)
