"""Configuration management for Grove."""

from pathlib import Path
import tomllib  # Built-in Python 3.11+
from typing import TypedDict


class GroveConfig(TypedDict):
    """Type definition for Grove configuration."""

    repo_path: str
    config_version: str


class Repository(TypedDict):
    """Type definition for a repository."""

    name: str
    path: str


class ConfigError(Exception):
    """Raised when config file is invalid or missing required fields."""

    pass


# Global state for active repository
_active_repo_path: Path | None = None


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


def load_config() -> dict:
    """Load configuration from TOML file.

    Returns:
        dict with config_version, last_used, and repositories list

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

    # Check config version and migrate if needed
    config_version = config_data.get("grove", {}).get("config_version", "1.0")

    if config_version == "1.0":
        # Auto-migrate from v1.0 to v2.0
        config_data = migrate_v1_to_v2(config_data)
        # Save migrated config
        try:
            _write_config(config_data)
        except Exception as e:
            raise ConfigError(f"Failed to save migrated config: {e}")

    # Validate v2.0 structure
    if "repositories" not in config_data or not isinstance(config_data["repositories"], list):
        raise ConfigError("Config missing or invalid [[repositories]] section")

    # Validate all repository paths
    for repo in config_data["repositories"]:
        if "path" not in repo:
            raise ConfigError(f"Repository missing 'path' field: {repo}")

        repo_path_obj = Path(repo["path"]).expanduser()
        if not repo_path_obj.exists():
            raise ConfigError(f"Repository path does not exist: {repo['path']}")

        if not (repo_path_obj / ".bare").is_dir():
            raise ConfigError(f"Repository path does not contain .bare directory: {repo['path']}")

    return config_data


def _write_config(config_data: dict) -> None:
    """Internal helper to write config data to file.

    Args:
        config_data: Complete config dictionary to write

    Raises:
        ConfigError: If unable to write config file
    """
    try:
        import tomli_w
    except ImportError:
        raise ConfigError("tomli-w package required for writing config files")

    config_path = get_config_path()

    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "wb") as f:
            tomli_w.dump(config_data, f)
    except Exception as e:
        raise ConfigError(f"Failed to write config file: {e}")


def get_repositories() -> list[Repository]:
    """Get list of all configured repositories.

    Returns:
        List of Repository dicts with name and path

    Raises:
        ConfigError: If config is invalid
    """
    try:
        config = load_config()
    except ConfigError:
        # If no config exists, return empty list
        return []

    return config.get("repositories", [])


def add_repository(path: str) -> None:
    """Add a repository to the config.

    Auto-generates name from directory name.

    Args:
        path: Absolute path to repository containing .bare directory

    Raises:
        ConfigError: If path is invalid or unable to write config
    """
    # Validate path
    repo_path_obj = Path(path).expanduser().resolve()
    if not (repo_path_obj / ".bare").is_dir():
        raise ConfigError(f"Invalid repository path (no .bare directory): {path}")

    # Auto-generate name from directory name
    name = repo_path_obj.name

    # Load existing config or create new one
    try:
        config_data = load_config()
    except ConfigError:
        # No config exists, create new one
        config_data = {
            "grove": {"config_version": "2.0"},
            "repositories": [],
        }

    # Check for duplicate paths
    for repo in config_data["repositories"]:
        if repo["path"] == str(repo_path_obj):
            # Update name if path already exists
            repo["name"] = name
            _write_config(config_data)
            return

    # Add new repository
    config_data["repositories"].append({"name": name, "path": str(repo_path_obj)})

    _write_config(config_data)


def remove_repository(path: str) -> None:
    """Remove a repository from the config.

    Args:
        path: Path to repository to remove

    Raises:
        ConfigError: If config is invalid or unable to write
    """
    config_data = load_config()

    # Remove repository with matching path
    repo_path_str = str(Path(path).expanduser().resolve())
    config_data["repositories"] = [r for r in config_data["repositories"] if r["path"] != repo_path_str]

    # If removed repo was last_used, remove the field (TOML doesn't support None)
    if config_data.get("grove", {}).get("last_used") == repo_path_str:
        if "last_used" in config_data.get("grove", {}):
            del config_data["grove"]["last_used"]

    _write_config(config_data)


def update_last_used(path: str) -> None:
    """Update the last_used repository in config.

    Args:
        path: Path to repository that was last used

    Raises:
        ConfigError: If config is invalid or unable to write
    """
    config_data = load_config()

    config_data.setdefault("grove", {})["last_used"] = str(Path(path).expanduser().resolve())

    _write_config(config_data)


def set_active_repo(path: Path) -> None:
    """Set the active repository (global state).

    Args:
        path: Path to repository to set as active

    Raises:
        ConfigError: If path is invalid
    """
    global _active_repo_path

    # Validate path
    repo_path_obj = path.expanduser().resolve()
    if not repo_path_obj.exists():
        raise ConfigError(f"Repository path does not exist: {path}")

    if not (repo_path_obj / ".bare").is_dir():
        raise ConfigError(f"Repository path does not contain .bare directory: {path}")

    _active_repo_path = repo_path_obj


def get_active_repo() -> Path:
    """Get the currently active repository.

    Returns:
        Path to active repository

    Raises:
        ConfigError: If no active repository is set
    """
    if _active_repo_path is None:
        raise ConfigError("No active repository set")

    return _active_repo_path


def get_repo_path() -> Path:
    """Get repository path (returns active repository).

    This is the main function used throughout the codebase to replace
    get_bare_parent() and .bare directory checks.

    Returns:
        Path to repository root (parent of .bare directory)

    Raises:
        ConfigError: If no active repository is set
    """
    return get_active_repo()


def find_repo_for_directory(cwd: Path) -> Path | None:
    """Find a configured repository that contains the given directory.

    Args:
        cwd: Current working directory to check

    Returns:
        Path to repository if found, None otherwise
    """
    repos = get_repositories()

    for repo in repos:
        repo_path = Path(repo["path"]).expanduser().resolve()
        try:
            # Check if cwd is inside this repository
            cwd.resolve().relative_to(repo_path)
            return repo_path
        except ValueError:
            # cwd is not relative to this repo, continue
            continue

    return None


def migrate_v1_to_v2(config_data: dict) -> dict:
    """Migrate v1.0 config to v2.0 format.

    Args:
        config_data: v1.0 config dictionary

    Returns:
        v2.0 config dictionary

    Raises:
        ConfigError: If v1.0 config is invalid
    """
    if "repository" not in config_data or "repo_path" not in config_data["repository"]:
        raise ConfigError("Invalid v1.0 config: missing [repository] section or repo_path")

    repo_path = config_data["repository"]["repo_path"]
    name = Path(repo_path).name

    return {
        "grove": {"config_version": "2.0", "last_used": repo_path},
        "repositories": [{"name": name, "path": repo_path}],
    }


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
