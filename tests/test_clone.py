"""Tests for repository cloning functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from git.exc import GitCommandError

from src.clone import (
    clone_repository,
    _is_valid_git_url,
    _extract_repo_name,
    _cleanup_failed_clone,
)


class TestURLValidation:
    """Tests for Git URL validation."""

    def test_valid_https_url(self) -> None:
        """Test that HTTPS URLs are validated correctly."""
        assert _is_valid_git_url("https://github.com/user/repo.git") is True
        assert _is_valid_git_url("https://gitlab.com/user/project") is True

    def test_valid_http_url(self) -> None:
        """Test that HTTP URLs are validated correctly."""
        assert _is_valid_git_url("http://github.com/user/repo.git") is True

    def test_valid_ssh_url(self) -> None:
        """Test that SSH URLs are validated correctly."""
        assert _is_valid_git_url("git@github.com:user/repo.git") is True
        assert _is_valid_git_url("ssh://git@github.com/user/repo.git") is True

    def test_valid_git_protocol(self) -> None:
        """Test that git:// URLs are validated correctly."""
        assert _is_valid_git_url("git://github.com/user/repo.git") is True

    def test_valid_file_url(self) -> None:
        """Test that file:// URLs are validated correctly."""
        assert _is_valid_git_url("file:///path/to/repo") is True

    def test_invalid_url(self) -> None:
        """Test that invalid URLs are rejected."""
        assert _is_valid_git_url("") is False
        assert _is_valid_git_url("not-a-url") is False
        assert _is_valid_git_url("/local/path") is False


class TestRepoNameExtraction:
    """Tests for extracting repository name from URL."""

    def test_https_url_with_git_extension(self) -> None:
        """Test extracting name from HTTPS URL with .git."""
        assert _extract_repo_name("https://github.com/user/repo.git") == "repo"

    def test_https_url_without_git_extension(self) -> None:
        """Test extracting name from HTTPS URL without .git."""
        assert (
            _extract_repo_name("https://gitlab.com/user/my-project") == "my-project"
        )

    def test_ssh_url(self) -> None:
        """Test extracting name from SSH URL."""
        assert _extract_repo_name("git@github.com:user/repo.git") == "repo"

    def test_url_with_trailing_slash(self) -> None:
        """Test extracting name from URL with trailing slash."""
        assert _extract_repo_name("https://github.com/user/repo.git/") == "repo"

    def test_complex_ssh_url(self) -> None:
        """Test extracting name from complex SSH URL."""
        assert _extract_repo_name("git@gitlab.com:org/team/project.git") == "project"


class TestCloneRepository:
    """Tests for clone_repository function."""

    @patch("src.clone.Repo")
    @patch("src.clone.add_repository")
    def test_successful_clone(
        self, mock_add_repo: MagicMock, mock_repo_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful repository clone."""
        # Setup
        test_url = "https://github.com/user/test-repo.git"

        # Change to tmp directory
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock GitPython
            mock_repo = MagicMock()
            mock_repo_class.clone_from.return_value = mock_repo
            mock_repo_class.return_value = mock_repo

            # Mock config writer
            mock_config = MagicMock()
            mock_repo.config_writer.return_value.__enter__.return_value = mock_config

            # Execute
            result = clone_repository(test_url)

            # Verify
            assert result == 0

            # Check directory structure was created
            target_dir = tmp_path / "test-repo"
            assert target_dir.exists()
            assert (target_dir / ".git").exists()
            assert (target_dir / ".worktree-setup").exists()
            assert (target_dir / ".worktree-teardown").exists()
            assert (target_dir / ".grove").exists()
            assert (target_dir / ".grove" / "metadata").exists()

            # Check .git file content
            git_file_content = (target_dir / ".git").read_text()
            assert git_file_content == "gitdir: ./.bare\n"

            # Check GitPython was called correctly
            mock_repo_class.clone_from.assert_called_once_with(
                test_url, str(target_dir / ".bare"), bare=True
            )

            # Check config was updated
            mock_config.set_value.assert_called_once_with(
                'remote "origin"', "fetch", "+refs/heads/*:refs/remotes/origin/*"
            )

            # Check repository was registered
            mock_add_repo.assert_called_once_with(str(target_dir))

            # Check scripts are executable
            assert (target_dir / ".worktree-setup").stat().st_mode & 0o111 != 0
            assert (target_dir / ".worktree-teardown").stat().st_mode & 0o111 != 0

        finally:
            os.chdir(original_cwd)

    @patch("src.clone.Repo")
    @patch("src.clone.add_repository")
    def test_clone_with_custom_name(
        self, mock_add_repo: MagicMock, mock_repo_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test cloning with custom directory name."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            test_url = "https://github.com/user/test-repo.git"
            custom_name = "my-custom-name"

            mock_repo = MagicMock()
            mock_repo_class.clone_from.return_value = mock_repo
            mock_repo_class.return_value = mock_repo
            mock_repo.config_writer.return_value.__enter__.return_value = MagicMock()

            result = clone_repository(test_url, custom_name)

            assert result == 0
            target_dir = tmp_path / custom_name
            assert target_dir.exists()
            mock_add_repo.assert_called_once_with(str(target_dir))

        finally:
            os.chdir(original_cwd)

    def test_clone_fails_for_invalid_url(self, tmp_path: Path) -> None:
        """Test that clone fails for invalid URL."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = clone_repository("not-a-valid-url")
            assert result == 1
        finally:
            os.chdir(original_cwd)

    @patch("src.clone.Repo")
    def test_clone_fails_if_directory_exists(
        self, mock_repo_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test that clone fails if target directory already exists."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            test_url = "https://github.com/user/test-repo.git"

            # Create directory first
            existing_dir = tmp_path / "test-repo"
            existing_dir.mkdir()

            result = clone_repository(test_url)

            assert result == 1
            mock_repo_class.clone_from.assert_not_called()

        finally:
            os.chdir(original_cwd)

    @patch("src.clone.Repo")
    @patch("src.clone._cleanup_failed_clone")
    def test_clone_cleanup_on_git_error(
        self, mock_cleanup: MagicMock, mock_repo_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test that failed clone triggers cleanup."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            test_url = "https://github.com/user/test-repo.git"

            # Simulate Git error
            mock_repo_class.clone_from.side_effect = GitCommandError("clone", "error")

            result = clone_repository(test_url)

            assert result == 1
            target_dir = tmp_path / "test-repo"
            mock_cleanup.assert_called_once_with(target_dir)

        finally:
            os.chdir(original_cwd)

    @patch("src.clone.Repo")
    @patch("src.clone.add_repository")
    def test_clone_continues_on_config_error(
        self, mock_add_repo: MagicMock, mock_repo_class: MagicMock, tmp_path: Path
    ) -> None:
        """Test that clone continues even if config registration fails."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            test_url = "https://github.com/user/test-repo.git"

            # Mock successful clone
            mock_repo = MagicMock()
            mock_repo_class.clone_from.return_value = mock_repo
            mock_repo_class.return_value = mock_repo
            mock_repo.config_writer.return_value.__enter__.return_value = MagicMock()

            # Mock config registration failure
            from src.config import ConfigError

            mock_add_repo.side_effect = ConfigError("Config error")

            # Clone should still succeed despite config error
            result = clone_repository(test_url)

            assert result == 0

        finally:
            os.chdir(original_cwd)


class TestCleanup:
    """Tests for cleanup functionality."""

    def test_cleanup_removes_directory(self, tmp_path: Path) -> None:
        """Test that cleanup removes the target directory."""
        test_dir = tmp_path / "test-cleanup"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        assert test_dir.exists()

        _cleanup_failed_clone(test_dir)

        assert not test_dir.exists()

    def test_cleanup_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that cleanup handles non-existent directory gracefully."""
        test_dir = tmp_path / "nonexistent"

        # Should not raise
        _cleanup_failed_clone(test_dir)

    def test_cleanup_handles_nested_directory(self, tmp_path: Path) -> None:
        """Test that cleanup handles nested directory structure."""
        test_dir = tmp_path / "test-cleanup"
        nested_dir = test_dir / "nested" / "deep"
        nested_dir.mkdir(parents=True)
        (nested_dir / "file.txt").write_text("content")

        assert test_dir.exists()

        _cleanup_failed_clone(test_dir)

        assert not test_dir.exists()
