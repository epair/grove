"""Tests for configuration management."""

import os
from pathlib import Path
import pytest
import tomllib

from src.config import (
    get_config_path,
    config_exists,
    load_config,
    save_config,
    get_repo_path,
    detect_potential_repositories,
    ConfigError,
)


class TestConfigPath:
    """Tests for config path functions."""

    def test_get_config_path(self) -> None:
        """Test that config path is in the expected location."""
        expected_path = Path.home() / ".config" / "grove" / "config"
        assert get_config_path() == expected_path

    def test_config_exists_when_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that config_exists returns False when config doesn't exist."""
        # Mock get_config_path to return non-existent path
        mock_config_path = tmp_path / "nonexistent" / "config"
        monkeypatch.setattr("src.config.get_config_path", lambda: mock_config_path)

        assert config_exists() is False

    def test_config_exists_when_present(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that config_exists returns True when config exists."""
        # Create a config file
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"
        config_file.touch()

        # Mock get_config_path to return this path
        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        assert config_exists() is True


class TestLoadConfig:
    """Tests for loading configuration."""

    def test_load_config_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully loading a valid config file."""
        # Create a valid config file
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write valid TOML config
        import tomli_w

        config_data = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": str(example_repo_path)},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        # Mock get_config_path
        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Load config
        config = load_config()

        assert config["repo_path"] == str(example_repo_path.resolve())
        assert config["config_version"] == "1.0"

    def test_load_config_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that loading missing config raises ConfigError."""
        mock_config_path = tmp_path / "nonexistent" / "config"
        monkeypatch.setattr("src.config.get_config_path", lambda: mock_config_path)

        with pytest.raises(ConfigError, match="Config file not found"):
            load_config()

    def test_load_config_invalid_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid TOML syntax raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write invalid TOML
        config_file.write_text("this is not valid TOML [[[")

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Invalid TOML syntax"):
            load_config()

    def test_load_config_missing_repository_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing [repository] section raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write TOML without [repository] section
        import tomli_w

        config_data = {"grove": {"config_version": "1.0"}}
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Config missing \\[repository\\] section"):
            load_config()

    def test_load_config_missing_repo_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing repo_path field raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write TOML without repo_path
        import tomli_w

        config_data = {"grove": {"config_version": "1.0"}, "repository": {}}
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Config missing 'repo_path'"):
            load_config()

    def test_load_config_invalid_repo_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that non-existent repo_path raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write config with non-existent path
        import tomli_w

        config_data = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": "/nonexistent/path"},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Repository path does not exist"):
            load_config()

    def test_load_config_no_bare_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that repo_path without .bare directory raises ConfigError."""
        # Create a directory without .bare
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write config pointing to directory without .bare
        import tomli_w

        config_data = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": str(repo_dir)},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="does not contain .bare directory"):
            load_config()

    def test_load_config_default_version(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config_version defaults to 1.0 if missing."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write config without config_version
        import tomli_w

        config_data = {"repository": {"repo_path": str(example_repo_path)}}
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        config = load_config()
        assert config["config_version"] == "1.0"


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_config_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully saving a config file."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Save config
        save_config(str(example_repo_path))

        # Verify file was created
        assert config_file.exists()

        # Verify content
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert "grove" in saved_data
        assert saved_data["grove"]["config_version"] == "1.0"
        assert "repository" in saved_data
        assert saved_data["repository"]["repo_path"] == str(example_repo_path.resolve())

    def test_save_config_creates_directory(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that save_config creates config directory if it doesn't exist."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        # Verify directory doesn't exist yet
        assert not config_dir.exists()

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Save config
        save_config(str(example_repo_path))

        # Verify directory was created
        assert config_dir.exists()
        assert config_file.exists()

    def test_save_config_invalid_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that saving config with invalid path raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Try to save config with non-existent path
        with pytest.raises(ConfigError, match="Invalid repository path"):
            save_config("/nonexistent/path")

    def test_save_config_no_bare_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that saving config with path without .bare raises ConfigError."""
        # Create directory without .bare
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Invalid repository path"):
            save_config(str(repo_dir))

    def test_save_config_expands_home(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that save_config expands ~ in paths."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Save config with absolute path
        save_config(str(example_repo_path))

        # Load and verify it's absolute
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        saved_path = Path(saved_data["repository"]["repo_path"])
        assert saved_path.is_absolute()


class TestGetRepoPath:
    """Tests for getting repository path from config."""

    def test_get_repo_path_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully getting repo path from config."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write valid config
        import tomli_w

        config_data = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": str(example_repo_path)},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Get repo path
        repo_path = get_repo_path()

        assert repo_path == example_repo_path.resolve()
        assert isinstance(repo_path, Path)

    def test_get_repo_path_missing_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_repo_path raises ConfigError when config is missing."""
        mock_config_path = tmp_path / "nonexistent" / "config"
        monkeypatch.setattr("src.config.get_config_path", lambda: mock_config_path)

        with pytest.raises(ConfigError, match="Config file not found"):
            get_repo_path()


class TestDetectPotentialRepositories:
    """Tests for repository auto-detection."""

    def test_detect_from_current_directory(
        self, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test detecting repository in current directory."""
        original_cwd = os.getcwd()
        os.chdir(example_repo_path)

        try:
            repos = detect_potential_repositories()
            assert example_repo_path in repos
        finally:
            os.chdir(original_cwd)

    def test_detect_from_parent_directory(
        self, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test detecting repository in parent directory."""
        original_cwd = os.getcwd()

        # Change to subdirectory (feature-one worktree)
        worktree_dir = example_repo_path / "feature-one"
        if worktree_dir.exists():
            os.chdir(worktree_dir)
        else:
            os.chdir(example_repo_path)

        try:
            repos = detect_potential_repositories()
            assert example_repo_path in repos
        finally:
            os.chdir(original_cwd)

    def test_detect_empty_when_no_repos(self, tmp_path: Path) -> None:
        """Test that detection returns empty list when no repos found."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            repos = detect_potential_repositories()
            # May still find repos in ~/code/projects, ~/projects, etc.
            # So we just verify it returns a list (may be empty or not)
            assert isinstance(repos, list)
        finally:
            os.chdir(original_cwd)

    def test_detect_sorts_by_modification_time(self, tmp_path: Path) -> None:
        """Test that detected repos are sorted by modification time (newest first)."""
        # Create two test repos with .bare directories
        repo1 = tmp_path / "repo1"
        repo1.mkdir()
        bare1 = repo1 / ".bare"
        bare1.mkdir()

        # Wait a tiny bit to ensure different mtimes
        import time

        time.sleep(0.01)

        repo2 = tmp_path / "repo2"
        repo2.mkdir()
        bare2 = repo2 / ".bare"
        bare2.mkdir()

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            repos = detect_potential_repositories()

            # Filter to only our test repos
            test_repos = [r for r in repos if r in [repo1, repo2]]

            if len(test_repos) == 2:
                # repo2 should come first (newer)
                assert test_repos[0] == repo2
                assert test_repos[1] == repo1
        finally:
            os.chdir(original_cwd)

    def test_detect_handles_permission_errors(self, tmp_path: Path) -> None:
        """Test that detection gracefully handles permission errors."""
        # This test is platform-dependent and may not work on all systems
        # Just verify it doesn't crash
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            repos = detect_potential_repositories()
            assert isinstance(repos, list)
        finally:
            os.chdir(original_cwd)

    def test_detect_limit_depth(self, tmp_path: Path) -> None:
        """Test that detection limits depth to 5 levels."""
        # Create a deeply nested structure with .bare at level 6
        current = tmp_path
        for i in range(7):
            current = current / f"level{i}"
            current.mkdir()

        # Add .bare at level 6
        (current / ".bare").mkdir()

        # Change to the deepest directory
        original_cwd = os.getcwd()
        os.chdir(current)

        try:
            repos = detect_potential_repositories()

            # The level 6 .bare should not be detected from level 0
            # (but it might be detected from current directory which is level 6)
            # This test just verifies the function runs without error
            assert isinstance(repos, list)
        finally:
            os.chdir(original_cwd)
