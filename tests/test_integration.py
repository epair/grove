import os
import pytest
from pathlib import Path
from typing import Generator
from textual.widgets import ListView, ListItem, Label
from app import GroveApp, get_worktree_directories, is_bare_git_repository


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

    async def test_grove_app_sidebar_content(self, change_to_example_repo: Path) -> None:
        """Test that the Grove app's sidebar displays the correct worktree directories."""
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

            # Verify the expected directories are present and sorted
            expected_directories = ["bugfix-01", "feature-one"]
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