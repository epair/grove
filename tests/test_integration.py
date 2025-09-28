import os
import pytest
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch
from textual.widgets import ListView, ListItem, Label
from app import GroveApp, get_worktree_directories, is_bare_git_repository, get_active_tmux_sessions, get_worktree_metadata, get_worktree_git_info, MetadataDisplay


class TestGroveIntegration:
    """Integration tests for Grove TUI worktree directory listing."""

    @pytest.fixture
    def example_repo_path(self) -> Path:
        """Fixture that provides the path to the example repo."""
        return Path(__file__).parent / "example_repo"

    @pytest.fixture
    def change_to_example_repo(self, example_repo_path: Path) -> Generator[Path, None, None]:
        """Fixture that temporarily changes working directory to example repo."""
        original_cwd = os.getcwd()
        os.chdir(example_repo_path)
        yield example_repo_path
        os.chdir(original_cwd)

    def test_is_bare_git_repository_detection(self, change_to_example_repo: Path) -> None:
        """Test that the bare git repository is correctly detected."""
        assert is_bare_git_repository() is True

    def test_get_worktree_directories(self, change_to_example_repo: Path) -> None:
        """Test that worktree directories are correctly identified and sorted."""
        directories = get_worktree_directories()

        # Should contain the two worktree directories from example_repo
        expected_directories = ["bugfix-01", "feature-one"]
        assert directories == expected_directories

        # Verify hidden directories are excluded
        assert ".bare" not in directories
        assert ".git" not in directories
        assert ".grove" not in directories

    @patch('app.get_active_tmux_sessions')
    async def test_grove_app_sidebar_content(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that the Grove app's sidebar displays the correct worktree directories with icons."""
        # Mock no tmux sessions for consistent testing
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Get the sidebar widget
            sidebar = app.query_one("#sidebar", ListView)

            # Get all list items in the sidebar
            list_items = sidebar.query(ListItem)

            # Extract the text content from each list item
            directory_labels = []
            for item in list_items:
                label = item.query_one(Label)
                directory_labels.append(str(label.content))

            # Verify the expected directories are present with empty circle icons
            expected_directories = ["○ bugfix-01", "○ feature-one"]
            assert directory_labels == expected_directories

    async def test_grove_app_starts_successfully(self, change_to_example_repo: Path) -> None:
        """Test that the Grove app starts successfully in a bare git repository."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Verify the app is running and main widgets are present
            assert app.query_one("#sidebar", ListView) is not None
            assert app.query_one("#body") is not None

            # Verify the sidebar is not empty
            sidebar = app.query_one("#sidebar", ListView)
            list_items = sidebar.query(ListItem)
            assert len(list_items) > 0

    def test_get_worktree_directories_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_directories returns empty list when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            directories = get_worktree_directories()
            assert directories == []
        finally:
            os.chdir(original_cwd)

    def test_is_bare_git_repository_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that is_bare_git_repository returns False when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            assert is_bare_git_repository() is False
        finally:
            os.chdir(original_cwd)

    @patch('app.subprocess.run')
    def test_get_active_tmux_sessions_success(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions correctly parses tmux output."""
        from subprocess import CompletedProcess

        # Mock successful tmux command with session output
        mock_run.return_value = CompletedProcess(
            args=['tmux', 'list-sessions', '-F', '#{session_name}'],
            returncode=0,
            stdout='session1\nsession2\nfeature-one\n',
            stderr=''
        )

        sessions = get_active_tmux_sessions()
        expected_sessions = {'session1', 'session2', 'feature-one'}
        assert sessions == expected_sessions

    @patch('app.subprocess.run')
    def test_get_active_tmux_sessions_no_sessions(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions handles no sessions gracefully."""
        from subprocess import CompletedProcess

        # Mock tmux command with no sessions (returns empty output)
        mock_run.return_value = CompletedProcess(
            args=['tmux', 'list-sessions', '-F', '#{session_name}'],
            returncode=1,
            stdout='',
            stderr='no server running on /tmp/tmux-501/default'
        )

        sessions = get_active_tmux_sessions()
        assert sessions == set()

    @patch('app.subprocess.run')
    def test_get_active_tmux_sessions_tmux_not_found(self, mock_run: Any) -> None:
        """Test that get_active_tmux_sessions handles tmux not being installed."""
        # Mock FileNotFoundError when tmux is not installed
        mock_run.side_effect = FileNotFoundError("tmux command not found")

        sessions = get_active_tmux_sessions()
        assert sessions == set()

    @patch('app.get_active_tmux_sessions')
    async def test_sidebar_with_active_tmux_sessions(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows filled circles for directories with active tmux sessions."""
        # Mock tmux sessions where one matches a worktree directory
        mock_sessions.return_value = {'feature-one', 'other-session'}
        app = GroveApp()

        async with app.run_test() as pilot:
            # Get the sidebar widget
            sidebar = app.query_one("#sidebar", ListView)

            # Get all list items in the sidebar
            list_items = sidebar.query(ListItem)

            # Extract the text content from each list item
            directory_labels = []
            for item in list_items:
                label = item.query_one(Label)
                directory_labels.append(str(label.content))

            # Verify feature-one has filled circle, bugfix-01 has empty circle
            expected_directories = ["○ bugfix-01", "● feature-one"]
            assert directory_labels == expected_directories

    def test_get_worktree_metadata_with_content(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata reads metadata files correctly."""
        metadata = get_worktree_metadata("feature-one")

        # Verify all expected metadata keys are present
        assert "description" in metadata
        assert "pr" in metadata
        assert "notes" in metadata

        # Verify content matches what we expect from the test files
        assert "user authentication" in metadata["description"].lower()
        assert "PR #123" in metadata["pr"]
        assert "password reset" in metadata["notes"]

    def test_get_worktree_metadata_missing_worktree(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_metadata handles missing worktree gracefully."""
        metadata = get_worktree_metadata("nonexistent-worktree")

        # Should return empty dict for nonexistent worktree
        assert metadata == {}

    def test_get_worktree_metadata_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_metadata returns empty dict when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            metadata = get_worktree_metadata("any-worktree")
            assert metadata == {}
        finally:
            os.chdir(original_cwd)

    @patch('app.subprocess.run')
    def test_get_worktree_git_info_success(self, mock_run: Any, change_to_example_repo: Path) -> None:
        """Test that get_worktree_git_info correctly parses git log output."""
        from subprocess import CompletedProcess

        # Mock successful git log command
        mock_run.return_value = CompletedProcess(
            args=['git', '-C', 'feature-one', 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            returncode=0,
            stdout='Add authentication system\n2024-09-28 10:30:45 -0700\nJohn Doe <john@example.com>\n',
            stderr=''
        )

        git_info = get_worktree_git_info("feature-one")

        assert git_info["commit_message"] == "Add authentication system"
        assert git_info["commit_date"] == "2024-09-28 10:30:45 -0700"
        assert git_info["committer"] == "John Doe <john@example.com>"

    @patch('app.subprocess.run')
    def test_get_worktree_git_info_failure(self, mock_run: Any, change_to_example_repo: Path) -> None:
        """Test that get_worktree_git_info handles git command failure gracefully."""
        from subprocess import CompletedProcess

        # Mock failed git log command
        mock_run.return_value = CompletedProcess(
            args=['git', '-C', 'feature-one', 'log', '-1', '--format=%s%n%ci%n%an <%ae>'],
            returncode=1,
            stdout='',
            stderr='fatal: not a git repository'
        )

        git_info = get_worktree_git_info("feature-one")

        assert git_info["commit_message"] == "N/A"
        assert git_info["commit_date"] == "N/A"
        assert git_info["committer"] == "N/A"

    def test_get_worktree_git_info_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_git_info returns N/A values when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            git_info = get_worktree_git_info("any-worktree")
            assert git_info["commit_message"] == "N/A"
            assert git_info["commit_date"] == "N/A"
            assert git_info["committer"] == "N/A"
        finally:
            os.chdir(original_cwd)

    async def test_metadata_display_widget_update(self, change_to_example_repo: Path) -> None:
        """Test that MetadataDisplay widget updates content correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Test updating with a valid worktree
            metadata_display.update_content("feature-one")
            content = str(metadata_display.source)

            # Verify the content contains expected sections
            assert "# feature-one" in content
            assert "## Description" in content
            assert "## Pull Request Info" in content
            assert "## Notes" in content
            assert "## Git Information" in content

            # Test updating with empty worktree name
            metadata_display.update_content("")
            content = str(metadata_display.source)
            assert "Select a worktree to view its metadata." in content

    @patch('app.get_active_tmux_sessions')
    async def test_sidebar_highlighting_updates_metadata(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that highlighting a worktree in sidebar updates the metadata display."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            sidebar = app.query_one("#sidebar", ListView)
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Simulate highlighting the first item (bugfix-01)
            sidebar.index = 0
            await pilot.pause()

            # Verify the selected worktree is updated
            assert app.selected_worktree == "bugfix-01"

            # Verify the metadata display shows bugfix-01 content
            content = str(metadata_display.source)
            assert "# bugfix-01" in content

    @patch('app.get_active_tmux_sessions')
    async def test_reactive_selected_worktree_updates_display(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that changing selected_worktree reactive attribute updates the display."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            metadata_display = app.query_one("#body", MetadataDisplay)

            # Change the reactive attribute directly
            app.selected_worktree = "feature-one"
            await pilot.pause()

            # Verify the metadata display is updated
            content = str(metadata_display.source)
            assert "# feature-one" in content
            assert "user authentication" in content.lower()