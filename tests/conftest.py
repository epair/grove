"""Shared fixtures and utilities for Grove tests."""

import os
import pytest
from pathlib import Path
from typing import Generator


@pytest.fixture
def example_repo_path() -> Path:
    """Fixture that provides the path to the example repo."""
    return Path(__file__).parent / "example_repo"


@pytest.fixture
def change_to_example_repo(example_repo_path: Path) -> Generator[Path, None, None]:
    """Fixture that temporarily changes working directory to example repo."""
    original_cwd = os.getcwd()
    os.chdir(example_repo_path)
    yield example_repo_path
    os.chdir(original_cwd)


@pytest.fixture(autouse=True)
def mock_config(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    example_repo_path: Path,
    monkeypatch: pytest.MonkeyPatch
) -> Path | None:
    """Auto-use fixture that sets up config for all tests except config tests.

    Skip this fixture for tests in test_config.py to avoid conflicts.
    """
    # Skip for config tests - they manage their own config
    if "test_config" in request.node.nodeid:
        return None

    config_dir = tmp_path / ".config" / "grove"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config"

    # Write config with example_repo path
    import tomli_w

    config_data = {
        "grove": {"config_version": "1.0"},
        "repository": {"repo_path": str(example_repo_path)},
    }
    with open(config_file, "wb") as f:
        tomli_w.dump(config_data, f)

    # Mock get_config_path to return our temp config
    from src import config

    monkeypatch.setattr(config, "get_config_path", lambda: config_file)

    return config_file