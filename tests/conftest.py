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