"""Repository cloning functionality for Grove."""

import sys
from pathlib import Path
from git import Repo
from git.exc import GitCommandError

from .config import add_repository, ConfigError


def clone_repository(url: str, name: str | None = None) -> int:
    """Clone a repository as bare and set up Grove structure.

    Args:
        url: Git repository URL to clone
        name: Optional directory name (defaults to repo name from URL)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Step 1: Validate URL format (basic check)
    if not _is_valid_git_url(url):
        print(f"Error: Invalid Git URL: {url}", file=sys.stderr)
        return 1

    # Step 2: Extract repository name from URL
    basename = _extract_repo_name(url)
    target_name = name if name else basename

    # Step 3: Determine target directory (current dir + target_name)
    target_dir = Path.cwd() / target_name

    # Step 4: Check if directory already exists
    if target_dir.exists():
        print(f"Error: Directory already exists: {target_dir}", file=sys.stderr)
        return 1

    try:
        # Step 5: Create target directory
        print(f"Cloning repository from {url}...")
        target_dir.mkdir(parents=True, exist_ok=False)

        # Step 6: Clone as bare repository to .bare subdirectory
        print(f"Creating bare repository at {target_dir}/.bare")
        bare_path = target_dir / ".bare"
        Repo.clone_from(url, str(bare_path), bare=True)

        # Step 7: Create .git file pointing to .bare
        print("Setting up git configuration...")
        git_file = target_dir / ".git"
        git_file.write_text("gitdir: ./.bare\n")

        # Step 8: Configure remote.origin.fetch for worktree branches
        bare_repo = Repo(str(bare_path))
        with bare_repo.config_writer() as config:
            config.set_value(
                'remote "origin"', "fetch", "+refs/heads/*:refs/remotes/origin/*"
            )

        # Step 9: Create .worktree-setup and .worktree-teardown files
        print("Creating worktree setup scripts...")
        setup_script = target_dir / ".worktree-setup"
        setup_script.touch(mode=0o755, exist_ok=True)

        teardown_script = target_dir / ".worktree-teardown"
        teardown_script.touch(mode=0o755, exist_ok=True)

        # Step 10: Create .grove directory structure
        print("Creating Grove directory structure...")
        grove_dir = target_dir / ".grove"
        grove_dir.mkdir(exist_ok=True)

        metadata_dir = grove_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)

        # Step 11: Register repository in Grove config
        print("Registering repository in Grove config...")
        try:
            add_repository(str(target_dir))
        except ConfigError as e:
            print(
                f"Warning: Failed to register repository in config: {e}",
                file=sys.stderr,
            )
            print(
                "You can add it manually later using the repository selection screen.",
                file=sys.stderr,
            )

        # Step 12: Success message
        print(f"\nSuccessfully cloned repository to {target_dir}")
        print(f"Run 'cd {target_name} && grove' to open this repository.")
        return 0

    except GitCommandError as e:
        print(f"Git error: {e}", file=sys.stderr)
        _cleanup_failed_clone(target_dir)
        return 1
    except PermissionError as e:
        print(f"Permission error: {e}", file=sys.stderr)
        _cleanup_failed_clone(target_dir)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        _cleanup_failed_clone(target_dir)
        return 1


def _is_valid_git_url(url: str) -> bool:
    """Validate that URL looks like a git repository URL.

    Accepts:
    - https://github.com/user/repo.git
    - git@github.com:user/repo.git
    - https://gitlab.com/user/repo
    - file:///path/to/repo

    Args:
        url: URL to validate

    Returns:
        True if URL appears valid, False otherwise
    """
    if not url:
        return False

    # Check for common patterns
    valid_patterns = [
        url.startswith("https://"),
        url.startswith("http://"),
        url.startswith("git@"),
        url.startswith("ssh://"),
        url.startswith("file://"),
        url.startswith("git://"),
    ]

    return any(valid_patterns)


def _extract_repo_name(url: str) -> str:
    """Extract repository name from URL.

    Examples:
    - https://github.com/user/repo.git -> repo
    - git@github.com:user/my-project.git -> my-project
    - https://gitlab.com/user/project -> project

    Args:
        url: Git repository URL

    Returns:
        Repository name without .git extension
    """
    # Get the last part of the URL path
    basename = url.rstrip("/").split("/")[-1]

    # Handle SSH-style URLs (git@host:user/repo.git)
    if ":" in basename and not basename.startswith("http"):
        basename = basename.split(":")[-1].split("/")[-1]

    # Remove .git extension if present
    if basename.endswith(".git"):
        basename = basename[:-4]

    return basename


def _cleanup_failed_clone(target_dir: Path) -> None:
    """Clean up directory after failed clone.

    Args:
        target_dir: Directory to remove
    """
    if target_dir.exists():
        import shutil

        try:
            shutil.rmtree(target_dir)
        except Exception:
            # Silently ignore cleanup failures
            pass
