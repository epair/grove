"""Shared fixtures and utilities for Grove tests."""

import os
import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import patch


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
def patch_label_renderable():
    """Patch Label class to add renderable property for compatibility with app.py."""
    from textual.widgets import Label

    # Add renderable property to Label class
    def get_renderable(self):
        return self._Static__content if hasattr(self, '_Static__content') else ""

    # Monkey-patch the Label class
    Label.renderable = property(get_renderable)

    yield

    # Clean up after the test
    if hasattr(Label, 'renderable'):
        delattr(Label, 'renderable')