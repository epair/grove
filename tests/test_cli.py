"""Integration tests for CLI functionality."""

import pytest
import subprocess
import sys
from pathlib import Path


class TestCLI:
    """Integration tests for grove CLI."""

    def test_grove_help(self) -> None:
        """Test that grove --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "src", "--help"], capture_output=True, text=True
        )

        assert result.returncode == 0
        assert "grove" in result.stdout
        assert "Git Worktree and Tmux Session Manager" in result.stdout
        assert "clone" in result.stdout

    def test_grove_clone_help(self) -> None:
        """Test that grove clone --help works."""
        result = subprocess.run(
            [sys.executable, "-m", "src", "clone", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "usage: grove clone" in result.stdout
        assert "Git repository URL to clone" in result.stdout
        assert "Target directory name" in result.stdout

    def test_grove_clone_invalid_url(self, tmp_path: Path) -> None:
        """Test that grove clone rejects invalid URLs."""
        import os

        # Get project root directory
        project_root = Path(__file__).parent.parent

        result = subprocess.run(
            [sys.executable, "-m", "src", "clone", "not-a-valid-url"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )

        assert result.returncode == 1
        assert "Invalid Git URL" in result.stderr

    def test_grove_clone_existing_directory(self, tmp_path: Path) -> None:
        """Test that grove clone rejects existing directories."""
        import os

        # Get project root directory
        project_root = Path(__file__).parent.parent

        # Create directory first
        test_dir = tmp_path / "existing-dir"
        test_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src",
                "clone",
                "https://github.com/user/repo.git",
                "existing-dir",
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(project_root)},
        )

        assert result.returncode == 1
        assert "already exists" in result.stderr
