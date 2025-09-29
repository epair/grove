import os
import pytest
from pathlib import Path
from typing import Any, Generator
from unittest.mock import patch, MagicMock
from textual.widgets import ListView, ListItem, Label, Input, Button, Checkbox
from app import GroveApp, WorktreeFormScreen, ConfirmDeleteScreen, PRFormScreen, get_worktree_directories, is_bare_git_repository, get_active_tmux_sessions, get_worktree_metadata, get_worktree_git_info, get_worktree_pr_status, MetadataDisplay


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
            # Note: feature-one has a PR indicator because it has .env with WORKTREE_PR_PUBLISHED=true
            expected_directories = ["○ bugfix-01", "○ [bold]PR[/bold] feature-one"]
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

            # Verify feature-one has filled circle and PR indicator, bugfix-01 has empty circle
            expected_directories = ["○ bugfix-01", "● [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories

    def test_get_worktree_pr_status(self, change_to_example_repo: Path) -> None:
        """Test that get_worktree_pr_status correctly identifies worktrees with PRs."""
        pr_worktrees = get_worktree_pr_status()

        # feature-one has a .env file with WORKTREE_PR_PUBLISHED=true
        assert 'feature-one' in pr_worktrees
        # bugfix-01 doesn't have a .env file, so no PR
        assert 'bugfix-01' not in pr_worktrees

    def test_get_worktree_pr_status_outside_bare_repo(self, tmp_path: Path) -> None:
        """Test that get_worktree_pr_status returns empty set when not in a bare repo."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            pr_worktrees = get_worktree_pr_status()
            assert pr_worktrees == set()
        finally:
            os.chdir(original_cwd)

    @patch('app.get_active_tmux_sessions')
    @patch('app.get_worktree_pr_status')
    async def test_sidebar_with_pr_indicators(self, mock_pr_status: Any, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows PR indicators for worktrees with published PRs."""
        # Mock no tmux sessions but feature-one has a PR
        mock_sessions.return_value = set()
        mock_pr_status.return_value = {'feature-one'}
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

            # Verify feature-one has PR indicator, bugfix-01 doesn't
            expected_directories = ["○ bugfix-01", "○ [bold]PR[/bold] feature-one"]
            assert directory_labels == expected_directories

    @patch('app.get_active_tmux_sessions')
    @patch('app.get_worktree_pr_status')
    async def test_sidebar_with_tmux_and_pr_indicators(self, mock_pr_status: Any, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that sidebar shows both tmux and PR indicators correctly."""
        # Mock tmux session for bugfix-01 and PR for feature-one
        mock_sessions.return_value = {'bugfix-01'}
        mock_pr_status.return_value = {'feature-one'}
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

            # Verify bugfix-01 has filled circle, feature-one has PR indicator
            expected_directories = ["● bugfix-01", "○ [bold]PR[/bold] feature-one"]
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

    # New Worktree Creation Feature Tests

    @patch('app.get_active_tmux_sessions')
    async def test_n_keybinding_opens_worktree_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'n' opens the WorktreeFormScreen."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'n' key to trigger new worktree action
            await pilot.press("n")

            # Verify that a new screen (WorktreeFormScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, WorktreeFormScreen)

            # Verify form elements are present
            form = app.screen
            assert form.query_one("#title", Label) is not None
            assert form.query_one("#prefix_input", Input) is not None
            assert form.query_one("#name_input", Input) is not None
            assert form.query_one("#create_button", Button) is not None
            assert form.query_one("#cancel_button", Button) is not None

    @patch('app.get_active_tmux_sessions')
    async def test_worktree_form_initial_values(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that the WorktreeFormScreen has correct initial values."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Check prefix input has default value
            prefix_input = form.query_one("#prefix_input", Input)
            assert prefix_input.value == "ep/"

            # Check name input is empty
            name_input = form.query_one("#name_input", Input)
            assert name_input.value == ""

    @patch('app.get_active_tmux_sessions')
    async def test_cancel_button_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Cancel button closes the form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            # Verify we're on the form screen
            assert isinstance(app.screen, WorktreeFormScreen)

            # Click cancel button
            await pilot.click("#cancel_button")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, WorktreeFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_escape_key_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key closes the form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            # Verify we're on the form screen
            assert isinstance(app.screen, WorktreeFormScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, WorktreeFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_create_button_with_empty_name_validation(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that create button doesn't submit when name is empty."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set prefix but leave name empty
            prefix_input = form.query_one("#prefix_input", Input)
            prefix_input.value = "test/"

            # Click create button with empty name
            await pilot.click("#create_button")
            await pilot.pause()

            # Verify we're still on the form screen (validation prevented submission)
            assert isinstance(app.screen, WorktreeFormScreen)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_create_button_with_valid_data(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that create button submits form with valid data."""
        mock_sessions.return_value = set()
        # Mock successful subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_mock = MagicMock()
            app.exit = exit_mock  # type: ignore[method-assign]

            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set both prefix and name
            prefix_input = form.query_one("#prefix_input", Input)
            name_input = form.query_one("#name_input", Input)

            prefix_input.value = "test/"
            name_input.value = "my-feature"

            # Click create button
            await pilot.click("#create_button")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_enter_key_in_name_field_submits_form(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Enter in name field submits the form."""
        mock_sessions.return_value = set()
        # Mock successful subprocess calls
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_mock = MagicMock()
            app.exit = exit_mock  # type: ignore[method-assign]

            # Press 'n' to open the form
            await pilot.press("n")

            form = app.screen
            # Set both prefix and name
            prefix_input = form.query_one("#prefix_input", Input)
            name_input = form.query_one("#name_input", Input)

            prefix_input.value = "feature/"
            name_input.value = "awesome-feature"

            # Focus name input and press Enter
            name_input.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_creation_subprocess_calls(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree creation makes correct subprocess calls."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager command
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_called = False
            def mock_exit() -> None:
                nonlocal exit_called
                exit_called = True
            exit_mock = MagicMock(side_effect=mock_exit)
            app.exit = exit_mock  # type: ignore[method-assign]

            # Simulate form data from user input
            form_data = {"prefix": "ep/", "name": "test-feature"}

            # Call the handler directly
            app.handle_worktree_creation(form_data)

            # Verify subprocess calls were made correctly (should have at least 2 calls)
            assert mock_subprocess.call_count >= 2

            # Find the worktree-manager and tmux-sessionizer calls
            worktree_call = None
            tmux_call = None

            for call in mock_subprocess.call_args_list:
                cmd = call[0][0]
                if cmd[0] == "worktree-manager":
                    worktree_call = call
                elif cmd[0] == "tmux-sessionizer":
                    tmux_call = call

            # Verify worktree-manager call
            assert worktree_call is not None
            assert worktree_call[0][0] == ["worktree-manager", "add", "test-feature"]
            assert worktree_call[1]["env"]["WORKTREE_PREFIX"] == "ep/"

            # Verify tmux-sessionizer call
            assert tmux_call is not None
            expected_path = str(Path.cwd() / "test-feature")
            assert tmux_call[0][0] == ["tmux-sessionizer", expected_path]

            # Verify app exit was called on success
            assert exit_called is True

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_creation_handles_command_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree creation handles command failures gracefully."""
        mock_sessions.return_value = set()

        # Mock failed worktree-manager command
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="Command failed")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.notify to track error messages
            notify_called = False
            notify_message = ""
            notify_severity = ""

            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                nonlocal notify_called, notify_message, notify_severity
                notify_called = True
                notify_message = message
                notify_severity = severity

            notify_mock = MagicMock(side_effect=mock_notify)
            app.notify = notify_mock  # type: ignore[method-assign]

            # Simulate form data from user input
            form_data = {"prefix": "ep/", "name": "test-feature"}

            # Call the handler directly
            app.handle_worktree_creation(form_data)

            # Verify error notification was shown
            assert notify_called is True
            assert "Failed to create worktree" in notify_message
            assert notify_severity == "error"

            # Verify worktree-manager was called but tmux-sessionizer was not
            worktree_call = None
            tmux_call = None

            for call in mock_subprocess.call_args_list:
                cmd = call[0][0]
                if cmd[0] == "worktree-manager":
                    worktree_call = call
                elif cmd[0] == "tmux-sessionizer":
                    tmux_call = call

            assert worktree_call is not None  # worktree-manager was called
            assert tmux_call is None  # tmux-sessionizer was not called

    async def test_worktree_creation_handles_cancel(self, change_to_example_repo: Path) -> None:
        """Test that worktree creation handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Call handler with None (cancelled form)
            app.handle_worktree_creation(None)

            # Should return immediately without doing anything (no assertion needed for None return)

    # Delete Worktree Feature Tests

    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_initial_state(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that ConfirmDeleteScreen displays correct initial content."""
        mock_sessions.return_value = set()
        app = GroveApp()
        worktree_name = "test-worktree"

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = worktree_name
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)
            screen = app.screen

            # Verify title
            title = screen.query_one("#delete_title", Label)
            assert str(title.content) == "Delete Worktree"

            # Verify message contains worktree name
            message = screen.query_one("#delete_message", Label)
            assert worktree_name in str(message.content)

            # Verify warning message
            warning = screen.query_one("#delete_warning", Label)
            assert "cannot be undone" in str(warning.content)

            # Verify buttons are present
            yes_button = screen.query_one("#yes_button", Button)
            no_button = screen.query_one("#no_button", Button)
            assert "Yes" in str(yes_button.label)
            assert "No" in str(no_button.label)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_yes_button(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Yes button confirms deletion."""
        mock_sessions.return_value = set()
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Click Yes button
            await pilot.click("#yes_button")
            await pilot.pause()

            # Verify we're back to main screen (deletion was confirmed)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_no_button(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking No button cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Click No button
            await pilot.click("#no_button")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_y_key(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'y' key confirms deletion."""
        mock_sessions.return_value = set()
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Press 'y' key
            await pilot.press("y")
            await pilot.pause()

            # Verify we're back to main screen (deletion was confirmed)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_n_key(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'n' key cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Press 'n' key
            await pilot.press("n")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_confirm_delete_screen_escape_key(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key cancels deletion."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set selected worktree and open delete confirmation
            app.selected_worktree = "test-worktree"
            await pilot.press("d")
            await pilot.pause()

            # Verify we're on the delete confirmation screen
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to main screen (deletion was cancelled)
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_d_keybinding_opens_delete_confirmation_with_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'd' opens delete confirmation when worktree is selected."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set a selected worktree
            app.selected_worktree = "feature-one"

            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'd' key to trigger delete action
            await pilot.press("d")
            await pilot.pause()

            # Verify that a new screen (ConfirmDeleteScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, ConfirmDeleteScreen)

            # Verify the screen was initialized with correct worktree name
            assert app.screen.worktree_name == "feature-one"

    @patch('app.get_active_tmux_sessions')
    async def test_d_keybinding_shows_warning_without_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'd' shows warning when no worktree is selected."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Ensure no worktree is selected
            app.selected_worktree = ""

            # Mock the notify method to capture notifications
            notify_called = False
            notify_message = ""
            notify_severity = ""

            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                nonlocal notify_called, notify_message, notify_severity
                notify_called = True
                notify_message = message
                notify_severity = severity

            app.notify = MagicMock(side_effect=mock_notify)

            # Press 'd' key
            await pilot.press("d")
            await pilot.pause()

            # Verify warning notification was shown
            assert notify_called is True
            assert "No worktree selected" in notify_message
            assert notify_severity == "warning"

            # Verify no modal screen was opened
            assert len(app.screen_stack) == 1

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_without_tmux_session(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when no corresponding tmux session exists."""
        mock_sessions.return_value = set()  # No active sessions

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning failure (session doesn't exist)
        tmux_has_session_result = MagicMock(returncode=1, stderr="session not found")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree with prefix
            app.selected_worktree = "ep/test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify worktree-manager remove was called correctly
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "ep/test-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == "ep/"

            # Verify tmux has-session was called
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]
            assert len(tmux_calls) == 1
            assert tmux_calls[0][0][0] == ["tmux", "has-session", "-t", "ep/test-feature"]

            # Verify success notification
            assert len(notifications) == 1
            assert "deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

            # Verify sidebar was refreshed
            assert sidebar.clear.called
            assert sidebar.append.called

            # Verify selected worktree was cleared
            assert app.selected_worktree == ""

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_successful_with_tmux_session(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test successful worktree deletion when corresponding tmux session exists."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning success (session exists)
        tmux_has_session_result = MagicMock(returncode=0, stderr="")

        # Mock successful tmux kill-session command
        tmux_kill_session_result = MagicMock(returncode=0, stderr="")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            elif cmd[0] == "tmux" and cmd[1] == "kill-session":
                return tmux_kill_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree with prefix
            app.selected_worktree = "feature/awesome-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify worktree-manager remove was called correctly
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "feature/awesome-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == "feature/"

            # Verify both tmux commands were called
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]
            assert len(tmux_calls) == 2

            # Check has-session call
            has_session_call = next(call for call in tmux_calls if call[0][0][1] == "has-session")
            assert has_session_call[0][0] == ["tmux", "has-session", "-t", "feature/awesome-feature"]

            # Check kill-session call
            kill_session_call = next(call for call in tmux_calls if call[0][0][1] == "kill-session")
            assert kill_session_call[0][0] == ["tmux", "kill-session", "-t", "feature/awesome-feature"]

            # Verify success notification mentions both worktree and tmux session
            assert len(notifications) == 1
            assert "and its tmux session deleted successfully" in notifications[0][0]
            assert notifications[0][1] == "information"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_worktree_manager_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles worktree-manager command failure."""
        mock_sessions.return_value = set()

        # Mock failed worktree-manager remove command
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="Failed to remove worktree")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to delete worktree" in notifications[0][0]
            assert notifications[0][1] == "error"

            # Verify only worktree-manager was called (no tmux commands)
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            tmux_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "tmux"]

            assert len(worktree_calls) == 1
            assert len(tmux_calls) == 0

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_tmux_kill_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles tmux kill-session failure gracefully."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        worktree_remove_result = MagicMock(returncode=0, stderr="")

        # Mock tmux has-session command returning success (session exists)
        tmux_has_session_result = MagicMock(returncode=0, stderr="")

        # Mock failed tmux kill-session command
        tmux_kill_session_result = MagicMock(returncode=1, stderr="Failed to kill session")

        # Configure subprocess.run to return different results based on command
        def subprocess_side_effect(cmd, **kwargs):
            if cmd[0] == "worktree-manager":
                return worktree_remove_result
            elif cmd[0] == "tmux" and cmd[1] == "has-session":
                return tmux_has_session_result
            elif cmd[0] == "tmux" and cmd[1] == "kill-session":
                return tmux_kill_session_result
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify warning notification was shown
            assert len(notifications) == 1
            assert "Worktree deleted but failed to kill tmux session" in notifications[0][0]
            assert notifications[0][1] == "warning"

    async def test_worktree_deletion_handles_cancellation(self, change_to_example_repo: Path) -> None:
        """Test that worktree deletion handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree
            app.selected_worktree = "test-feature"

            # Call handler with cancellation (False or None)
            app.handle_worktree_deletion(False)
            app.handle_worktree_deletion(None)

            # Should return immediately without doing anything (no assertion needed for early return)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_worktree_deletion_handles_no_prefix(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that worktree deletion works correctly for worktrees without prefix."""
        mock_sessions.return_value = set()

        # Mock successful worktree-manager remove command
        mock_subprocess.return_value = MagicMock(returncode=0, stderr="")

        app = GroveApp()

        async with app.run_test() as pilot:
            # Set up selected worktree without prefix (no slash)
            app.selected_worktree = "simple-feature"

            # Mock notifications to track messages
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))

            app.notify = MagicMock(side_effect=mock_notify)

            # Mock sidebar operations
            sidebar = app.query_one("#sidebar")
            sidebar.clear = MagicMock()
            sidebar.append = MagicMock()

            # Call deletion handler with confirmation
            app.handle_worktree_deletion(True)

            # Verify worktree-manager remove was called with empty prefix
            worktree_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0] == "worktree-manager"]
            assert len(worktree_calls) == 1
            assert worktree_calls[0][0][0] == ["worktree-manager", "remove", "simple-feature"]
            assert worktree_calls[0][1]["env"]["WORKTREE_PREFIX"] == ""

    @patch('app.get_active_tmux_sessions')
    async def test_delete_action_integration_with_sidebar_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test full integration of selecting worktree from sidebar and deleting it."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            sidebar = app.query_one("#sidebar", ListView)

            # Simulate highlighting the first item (bugfix-01)
            sidebar.index = 0
            await pilot.pause()

            # Verify the selected worktree is updated
            assert app.selected_worktree == "bugfix-01"

            # Press 'd' to open delete confirmation
            await pilot.press("d")
            await pilot.pause()

            # Verify delete confirmation screen is shown
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, ConfirmDeleteScreen)
            assert app.screen.worktree_name == "bugfix-01"

            # Press 'n' to cancel
            await pilot.press("n")
            await pilot.pause()

            # Verify we're back to main screen
            assert len(app.screen_stack) == 1
            assert not isinstance(app.screen, ConfirmDeleteScreen)

    # PR Creation Feature Tests

    @patch('app.get_active_tmux_sessions')
    async def test_p_keybinding_opens_pr_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'p' opens the PRFormScreen."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Set a selected worktree
            app.selected_worktree = "feature-one"

            # Initially, there should be no modal screen
            assert len(app.screen_stack) == 1

            # Press 'p' key to trigger create PR action
            await pilot.press("p")
            await pilot.pause()

            # Verify that a new screen (PRFormScreen) has been pushed
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen, PRFormScreen)

            # Verify form elements are present
            form = app.screen
            assert form.query_one("#pr_title", Label) is not None
            assert form.query_one("#pr_title_input", Input) is not None
            assert form.query_one("#reviewers_label", Label) is not None
            assert form.query_one("#create_pr_button", Button) is not None
            assert form.query_one("#cancel_pr_button", Button) is not None

    @patch('app.get_active_tmux_sessions')
    async def test_p_keybinding_shows_warning_without_selection(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing 'p' shows warning when no worktree is selected."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            # Ensure no worktree is selected
            app.selected_worktree = ""

            # Mock the notify method to capture notifications
            notify_called = False
            notify_message = ""
            notify_severity = ""

            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                nonlocal notify_called, notify_message, notify_severity
                notify_called = True
                notify_message = message
                notify_severity = severity

            app.notify = MagicMock(side_effect=mock_notify)

            # Press 'p' key
            await pilot.press("p")
            await pilot.pause()

            # Verify warning notification was shown
            assert notify_called is True
            assert "No worktree selected" in notify_message
            assert notify_severity == "warning"

            # Verify no modal screen was opened
            assert len(app.screen_stack) == 1

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_checkboxes_present(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that PR form has all required checkboxes."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Check all reviewer checkboxes are present
            reviewers = ["njm", "swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]
            for reviewer in reviewers:
                checkbox = form.query_one(f"#checkbox_{reviewer}", Checkbox)
                assert checkbox is not None
                assert reviewer in str(checkbox.label)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_njm_selected_by_default(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that 'njm' checkbox is selected by default."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Check that njm is selected by default
            njm_checkbox = form.query_one("#checkbox_njm", Checkbox)
            assert njm_checkbox.value is True

            # Check that others are not selected
            other_reviewers = ["swlkr", "daviswahl", "BryceFrye", "neddenriep", "gorilla076"]
            for reviewer in other_reviewers:
                checkbox = form.query_one(f"#checkbox_{reviewer}", Checkbox)
                assert checkbox.value is False

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_cancel_button_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that clicking Cancel button closes the PR form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            # Verify we're on the PR form screen
            assert isinstance(app.screen, PRFormScreen)

            # Click cancel button
            await pilot.click("#cancel_pr_button")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, PRFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_escape_key_closes_form(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Escape key closes the PR form."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            # Verify we're on the PR form screen
            assert isinstance(app.screen, PRFormScreen)

            # Press Escape key
            await pilot.press("escape")
            await pilot.pause()

            # Verify we're back to the main screen
            assert not isinstance(app.screen, PRFormScreen)

    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_validation_empty_title(self, mock_sessions: Any, change_to_example_repo: Path) -> None:
        """Test that PR form doesn't submit with empty title."""
        mock_sessions.return_value = set()
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Leave title empty
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = ""

            # Click create button with empty title
            await pilot.click("#create_pr_button")
            await pilot.pause()

            # Verify we're still on the form screen (validation prevented submission)
            assert isinstance(app.screen, PRFormScreen)

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_submission_with_valid_data(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form submits correctly with valid data."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            exit_called = False
            def mock_exit() -> None:
                nonlocal exit_called
                exit_called = True
            app.exit = MagicMock(side_effect=mock_exit)

            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Set PR title
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = "Add awesome feature"

            # Select additional reviewers
            checkbox_swlkr = form.query_one("#checkbox_swlkr", Checkbox)
            checkbox_swlkr.toggle()

            # Click create button
            await pilot.click("#create_pr_button")
            await pilot.pause()

            # Verify subprocess was called
            assert mock_subprocess.called

            # Verify git commands were called
            git_calls = [call for call in mock_subprocess.call_args_list if 'git' in call[0][0][0]]
            assert len(git_calls) >= 2  # branch and push

            # Verify gh command was called
            gh_calls = [call for call in mock_subprocess.call_args_list if 'gh' in call[0][0][0]]
            assert len(gh_calls) == 1

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_handles_git_push_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form handles git push failure gracefully."""
        mock_sessions.return_value = set()

        # Mock git branch success but push failure
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=1, stdout="", stderr="Failed to push")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock notify to track error
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))
            app.notify = MagicMock(side_effect=mock_notify)

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": ["njm"]}
            app.handle_pr_submission(form_data)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to push" in notifications[0][0]
            assert notifications[0][1] == "error"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_handles_gh_pr_create_failure(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form handles gh pr create failure gracefully."""
        mock_sessions.return_value = set()

        # Mock successful git commands but gh pr create failure
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=1, stdout="", stderr="Failed to create PR")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock notify to track error
            notifications = []
            def mock_notify(message: str, severity: str = "information", **kwargs: Any) -> None:
                notifications.append((message, severity))
            app.notify = MagicMock(side_effect=mock_notify)

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": ["njm", "swlkr"]}
            app.handle_pr_submission(form_data)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to create PR" in notifications[0][0]
            assert notifications[0][1] == "error"

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    @patch('app.Path.write_text')
    async def test_pr_form_writes_env_file(self, mock_write_text: Any, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that PR form writes WORKTREE_PR_PUBLISHED to .env file."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            elif 'open' in cmd[0]:
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            app.exit = MagicMock()

            app.selected_worktree = "feature-one"

            # Call handler directly with form data
            form_data = {"title": "Test PR", "reviewers": []}
            app.handle_pr_submission(form_data)

            # Verify .env file write was attempted
            assert mock_write_text.called
            written_content = mock_write_text.call_args[0][0]
            assert "WORKTREE_PR_PUBLISHED=true" in written_content

    @patch('app.subprocess.run')
    @patch('app.get_active_tmux_sessions')
    async def test_pr_form_enter_key_submission(self, mock_sessions: Any, mock_subprocess: Any, change_to_example_repo: Path) -> None:
        """Test that pressing Enter in title field submits the PR form."""
        mock_sessions.return_value = set()

        # Mock successful git and gh commands
        def subprocess_side_effect(cmd, **kwargs):
            if 'git' in cmd[0] and 'branch' in cmd:
                return MagicMock(returncode=0, stdout="test-branch", stderr="")
            elif 'git' in cmd[0] and 'push' in cmd:
                return MagicMock(returncode=0, stdout="", stderr="")
            elif 'gh' in cmd[0]:
                return MagicMock(returncode=0, stdout="https://github.com/user/repo/pull/123", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = subprocess_side_effect

        app = GroveApp()

        async with app.run_test() as pilot:
            # Mock app.exit to prevent actual exit
            app.exit = MagicMock()

            app.selected_worktree = "feature-one"
            await pilot.press("p")
            await pilot.pause()

            form = app.screen
            # Set PR title
            title_input = form.query_one("#pr_title_input", Input)
            title_input.value = "Quick PR via Enter"

            # Focus title input and press Enter
            title_input.focus()
            await pilot.press("enter")
            await pilot.pause()

            # Verify subprocess was called (form was submitted)
            assert mock_subprocess.called

    async def test_pr_form_handles_cancellation(self, change_to_example_repo: Path) -> None:
        """Test that PR form handles cancellation correctly."""
        app = GroveApp()

        async with app.run_test() as pilot:
            app.selected_worktree = "feature-one"

            # Call handler with None (cancelled form)
            app.handle_pr_submission(None)

            # Should return immediately without doing anything (no assertion needed for None return)