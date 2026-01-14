"""Configuration management for Grove."""

from pathlib import Path
import tomllib  # Built-in Python 3.11+
from typing import TypedDict


class GroveConfig(TypedDict):
    """Type definition for Grove configuration."""

    repo_path: str
    config_version: str


class ConfigError(Exception):
    """Raised when config file is invalid or missing required fields."""

    pass


def get_config_path() -> Path:
    """Get the path to the Grove config file.

    Returns:
        Path to ~/.config/grove/config
    """
    return Path.home() / ".config" / "grove" / "config"


def config_exists() -> bool:
    """Check if config file exists.

    Returns:
        True if config file exists, False otherwise
    """
    return get_config_path().exists()


def load_config() -> GroveConfig:
    """Load configuration from TOML file.

    Returns:
        GroveConfig dictionary with repo_path and config_version

    Raises:
        ConfigError: If config file is missing, invalid, or missing required fields
    """
    config_path = get_config_path()

    if not config_path.exists():
        raise ConfigError(f"Config file not found at {config_path}")

    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML syntax in config file: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read config file: {e}")

    # Validate required fields
    if "repository" not in config_data:
        raise ConfigError("Config missing [repository] section")

    if "repo_path" not in config_data["repository"]:
        raise ConfigError("Config missing 'repo_path' in [repository] section")

    repo_path = config_data["repository"]["repo_path"]

    # Validate repo_path exists and contains .bare
    repo_path_obj = Path(repo_path).expanduser()
    if not repo_path_obj.exists():
        raise ConfigError(f"Repository path does not exist: {repo_path}")

    if not (repo_path_obj / ".bare").is_dir():
        raise ConfigError(f"Repository path does not contain .bare directory: {repo_path}")

    return {
        "repo_path": str(repo_path_obj.resolve()),
        "config_version": config_data.get("grove", {}).get("config_version", "1.0"),
    }


def save_config(repo_path: str) -> None:
    """Save configuration to TOML file.

    Args:
        repo_path: Absolute path to repository containing .bare directory

    Raises:
        ConfigError: If unable to write config file
    """
    # Need tomli-w for writing TOML
    try:
        import tomli_w
    except ImportError:
        raise ConfigError("tomli-w package required for writing config files")

    config_path = get_config_path()

    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate repo_path before saving
    repo_path_obj = Path(repo_path).expanduser().resolve()
    if not (repo_path_obj / ".bare").is_dir():
        raise ConfigError(f"Invalid repository path (no .bare directory): {repo_path}")

    config_data = {
        "grove": {"config_version": "1.0"},
        "repository": {"repo_path": str(repo_path_obj)},
    }

    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(config_data, f)
    except Exception as e:
        raise ConfigError(f"Failed to write config file: {e}")


def get_repo_path() -> Path:
    """Get repository path from config.

    This is the main function used throughout the codebase to replace
    get_bare_parent() and .bare directory checks.

    Returns:
        Path to repository root (parent of .bare directory)

    Raises:
        ConfigError: If config is invalid or missing
    """
    config = load_config()
    return Path(config["repo_path"])


def detect_potential_repositories() -> list[Path]:
    """Auto-detect potential .bare repository locations on the system.

    Search strategy:
    1. Check current directory and parents (up to 5 levels)
    2. Check common project directories:
       - ~/code/projects/*
       - ~/projects/*
       - ~/dev/*
       - ~/workspace/*

    Returns:
        List of paths containing .bare directories, sorted by modification time (newest first)
    """
    candidates: list[tuple[Path, float]] = []

    # Strategy 1: Check current directory and parents
    current = Path.cwd()
    for i, parent in enumerate([current] + list(current.parents)):
        if i >= 5:  # Limit depth
            break
        if (parent / ".bare").is_dir():
            candidates.append((parent, (parent / ".bare").stat().st_mtime))

    # Strategy 2: Check common project directories
    home = Path.home()
    search_dirs = [
        home / "code" / "projects",
        home / "projects",
        home / "dev",
        home / "workspace",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        try:
            # Look for directories containing .bare (one level deep)
            for item in search_dir.iterdir():
                if item.is_dir() and (item / ".bare").is_dir():
                    candidates.append((item, (item / ".bare").stat().st_mtime))
        except (PermissionError, OSError):
            # Skip directories we can't read
            continue

    # Remove duplicates and sort by modification time (newest first)
    unique_paths = {path: mtime for path, mtime in candidates}
    sorted_paths = sorted(unique_paths.items(), key=lambda x: x[1], reverse=True)

    return [path for path, _ in sorted_paths]
