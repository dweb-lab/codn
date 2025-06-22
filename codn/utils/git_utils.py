import shutil
import subprocess  # nosec
from pathlib import Path
from typing import Union


def is_valid_git_repo(path: Union[str, Path]) -> bool:
    """Check if the given path is a valid and healthy Git repository.

    Args:
        path: Path to the root of a potential Git repository.

    Returns:
        True if the path is a valid, healthy Git repository, False otherwise.
    """
    repo_path = Path(path).resolve()
    git_dir = repo_path / ".git"

    if not git_dir.exists():
        return False

    # Check if git is available
    git_executable = shutil.which("git")
    if git_executable is None:
        print("Git command not found")
        return False

    try:
        # Check if we can access the current HEAD commit
        subprocess.run(  # nosec
            [git_executable, "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Check for repository corruption
        result = subprocess.run(  # nosec
            [git_executable, "-C", str(repo_path), "fsck"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output_lower = result.stdout.lower()
        if "missing" in output_lower or "error" in output_lower:
            print(f"Possible Git repository corruption: {result.stdout}")
            return False

        return True

    except subprocess.CalledProcessError as e:
        print(f"Git check failed: {e.stderr or e.stdout}")
        return False
    except subprocess.TimeoutExpired:
        print("Git command timed out")
        return False
    except FileNotFoundError:
        print("Git command not found")
        return False
