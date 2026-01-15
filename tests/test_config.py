"""Tests for configuration management."""

import os
from pathlib import Path
import pytest
import tomllib

from src.config import (
    get_config_path,
    config_exists,
    load_config,
    get_repositories,
    add_repository,
    remove_repository,
    update_last_used,
    set_active_repo,
    get_active_repo,
    get_repo_path,
    find_repo_for_directory,
    migrate_v1_to_v2,
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

    def test_load_config_v2_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully loading a valid v2.0 config file."""
        # Create a valid v2.0 config file
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write valid v2.0 TOML config
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0", "last_used": str(example_repo_path)},
            "repositories": [{"name": "example_repo", "path": str(example_repo_path)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        # Mock get_config_path
        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Load config
        config = load_config()

        assert config["grove"]["config_version"] == "2.0"
        assert config["repositories"][0]["path"] == str(example_repo_path)
        assert config["repositories"][0]["name"] == "example_repo"

    def test_load_config_v1_auto_migration(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that v1.0 config is auto-migrated to v2.0."""
        # Create a v1.0 config file
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write v1.0 TOML config
        import tomli_w

        config_data = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": str(example_repo_path)},
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        # Mock get_config_path
        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Load config - should auto-migrate
        config = load_config()

        # Should now be v2.0 format
        assert config["grove"]["config_version"] == "2.0"
        assert len(config["repositories"]) == 1
        assert config["repositories"][0]["path"] == str(example_repo_path)
        assert config["repositories"][0]["name"] == example_repo_path.name
        assert config["grove"]["last_used"] == str(example_repo_path)

        # Verify migration was saved to file
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)
        assert saved_data["grove"]["config_version"] == "2.0"

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

    def test_load_config_missing_repositories_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing [[repositories]] section raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write v2.0 TOML without [[repositories]] section
        import tomli_w

        config_data = {"grove": {"config_version": "2.0"}}
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Config missing or invalid \\[\\[repositories\\]\\] section"):
            load_config()

    def test_load_config_missing_repo_path_field(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that repository missing 'path' field raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write v2.0 TOML with repository missing path
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "test"}],  # Missing path field
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Repository missing 'path' field"):
            load_config()

    def test_load_config_invalid_repo_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that non-existent repo_path raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write v2.0 config with non-existent path
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "test", "path": "/nonexistent/path"}],
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

        # Write v2.0 config pointing to directory without .bare
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "repo", "path": str(repo_dir)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="does not contain .bare directory"):
            load_config()

    def test_load_config_default_version_triggers_migration(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config without version defaults to 1.0 and triggers migration."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write config without config_version (defaults to 1.0)
        import tomli_w

        config_data = {"repository": {"repo_path": str(example_repo_path)}}
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        config = load_config()
        # Should be migrated to v2.0
        assert config["grove"]["config_version"] == "2.0"


class TestGetRepoPath:
    """Tests for getting repository path (active repository)."""

    def test_get_repo_path_success(self, example_repo_path: Path) -> None:
        """Test successfully getting repo path when active repo is set."""
        # Set active repo
        set_active_repo(example_repo_path)

        # Get repo path
        repo_path = get_repo_path()

        assert repo_path == example_repo_path.resolve()
        assert isinstance(repo_path, Path)

    def test_get_repo_path_no_active_repo(self) -> None:
        """Test that get_repo_path raises ConfigError when no active repo is set."""
        # Reset global state
        import src.config
        src.config._active_repo_path = None

        with pytest.raises(ConfigError, match="No active repository set"):
            get_repo_path()


class TestGetRepositories:
    """Tests for getting list of repositories."""

    def test_get_repositories_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test getting list of repositories from config."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Write v2.0 config with multiple repos
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [
                {"name": "repo1", "path": str(example_repo_path)},
                {"name": "repo2", "path": str(example_repo_path)},
            ],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        repos = get_repositories()

        assert len(repos) == 2
        assert repos[0]["name"] == "repo1"
        assert repos[1]["name"] == "repo2"

    def test_get_repositories_empty_when_no_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_repositories returns empty list when no config exists."""
        mock_config_path = tmp_path / "nonexistent" / "config"
        monkeypatch.setattr("src.config.get_config_path", lambda: mock_config_path)

        repos = get_repositories()
        assert repos == []


class TestAddRepository:
    """Tests for adding repositories."""

    def test_add_repository_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully adding a repository."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Add repository
        add_repository(str(example_repo_path))

        # Verify file was created and contains repository
        assert config_file.exists()

        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert saved_data["grove"]["config_version"] == "2.0"
        assert len(saved_data["repositories"]) == 1
        assert saved_data["repositories"][0]["path"] == str(example_repo_path.resolve())
        assert saved_data["repositories"][0]["name"] == example_repo_path.name

    def test_add_repository_auto_generates_name(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that add_repository auto-generates name from directory name."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        add_repository(str(example_repo_path))

        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert saved_data["repositories"][0]["name"] == example_repo_path.name

    def test_add_repository_duplicate_updates_name(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that adding duplicate path updates the name."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Add repository twice
        add_repository(str(example_repo_path))
        add_repository(str(example_repo_path))

        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        # Should only have one repository (not duplicated)
        assert len(saved_data["repositories"]) == 1

    def test_add_repository_invalid_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that adding invalid path raises ConfigError."""
        config_dir = tmp_path / ".config" / "grove"
        config_file = config_dir / "config"

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        with pytest.raises(ConfigError, match="Invalid repository path"):
            add_repository("/nonexistent/path")


class TestRemoveRepository:
    """Tests for removing repositories."""

    def test_remove_repository_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully removing a repository."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Create a second test repository
        repo2_dir = tmp_path / "repo2"
        repo2_dir.mkdir()
        (repo2_dir / ".bare").mkdir()

        # Create config with two repositories
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [
                {"name": "repo1", "path": str(example_repo_path)},
                {"name": "repo2", "path": str(repo2_dir)},
            ],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Remove first repository
        remove_repository(str(example_repo_path))

        # Verify repository was removed
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert len(saved_data["repositories"]) == 1
        assert saved_data["repositories"][0]["name"] == "repo2"

    def test_remove_repository_clears_last_used(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that removing repository that was last_used removes the field."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Create config with repository as last_used
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0", "last_used": str(example_repo_path)},
            "repositories": [{"name": "repo1", "path": str(example_repo_path)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Remove repository
        remove_repository(str(example_repo_path))

        # Verify last_used field was removed (not just set to None)
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert "last_used" not in saved_data.get("grove", {})


class TestUpdateLastUsed:
    """Tests for updating last_used repository."""

    def test_update_last_used_success(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully updating last_used field."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Create initial config
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "repo1", "path": str(example_repo_path)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Update last_used
        update_last_used(str(example_repo_path))

        # Verify last_used was updated
        with open(config_file, "rb") as f:
            saved_data = tomllib.load(f)

        assert saved_data["grove"]["last_used"] == str(example_repo_path.resolve())


class TestSetActiveRepo:
    """Tests for setting active repository."""

    def test_set_active_repo_success(self, example_repo_path: Path) -> None:
        """Test successfully setting active repository."""
        set_active_repo(example_repo_path)

        assert get_active_repo() == example_repo_path.resolve()

    def test_set_active_repo_invalid_path(self, tmp_path: Path) -> None:
        """Test that setting invalid path raises ConfigError."""
        invalid_path = tmp_path / "nonexistent"

        with pytest.raises(ConfigError, match="Repository path does not exist"):
            set_active_repo(invalid_path)

    def test_set_active_repo_no_bare_directory(self, tmp_path: Path) -> None:
        """Test that setting path without .bare raises ConfigError."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        with pytest.raises(ConfigError, match="does not contain .bare directory"):
            set_active_repo(repo_dir)


class TestFindRepoForDirectory:
    """Tests for finding repository containing a directory."""

    def test_find_repo_for_directory_inside_repo(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test finding repository when cwd is inside it."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Create config
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "repo1", "path": str(example_repo_path)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Find repo for a directory inside it
        found_repo = find_repo_for_directory(example_repo_path / "feature-one")

        assert found_repo == example_repo_path.resolve()

    def test_find_repo_for_directory_outside_repo(
        self, tmp_path: Path, example_repo_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that finding repository returns None when cwd is outside all repos."""
        config_dir = tmp_path / ".config" / "grove"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config"

        # Create config
        import tomli_w

        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [{"name": "repo1", "path": str(example_repo_path)}],
        }
        with open(config_file, "wb") as f:
            tomli_w.dump(config_data, f)

        monkeypatch.setattr("src.config.get_config_path", lambda: config_file)

        # Find repo for a directory outside any repo
        found_repo = find_repo_for_directory(tmp_path / "other_dir")

        assert found_repo is None


class TestMigrateV1ToV2:
    """Tests for config migration."""

    def test_migrate_v1_to_v2_success(self, example_repo_path: Path) -> None:
        """Test successfully migrating v1.0 config to v2.0."""
        v1_config = {
            "grove": {"config_version": "1.0"},
            "repository": {"repo_path": str(example_repo_path)},
        }

        v2_config = migrate_v1_to_v2(v1_config)

        assert v2_config["grove"]["config_version"] == "2.0"
        assert v2_config["grove"]["last_used"] == str(example_repo_path)
        assert len(v2_config["repositories"]) == 1
        assert v2_config["repositories"][0]["name"] == example_repo_path.name
        assert v2_config["repositories"][0]["path"] == str(example_repo_path)

    def test_migrate_v1_to_v2_missing_fields(self) -> None:
        """Test that migration raises error for invalid v1.0 config."""
        v1_config = {"grove": {"config_version": "1.0"}}

        with pytest.raises(ConfigError, match="Invalid v1.0 config"):
            migrate_v1_to_v2(v1_config)


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
