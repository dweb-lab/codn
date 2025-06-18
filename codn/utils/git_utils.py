import os
import subprocess

def is_valid_git_repo(path: str) -> bool:
    """
    Checks whether the given path is a valid and healthy Git repository.

    Parameters:
        path (str): Path to the root of a potential Git repository.

    Returns:
        bool: True if the path is a valid, healthy Git repository, False otherwise.
    """
    git_dir = os.path.join(path, ".git")
    if not os.path.isdir(git_dir):
        return False

    try:
        # Check if we can access the current HEAD commit
        subprocess.check_output(['git', '-C', path, 'rev-parse', 'HEAD'],
                                stderr=subprocess.STDOUT)

        # Check for repository corruption (missing objects, etc.)
        fsck_output = subprocess.check_output(['git', '-C', path, 'fsck'],
                                              stderr=subprocess.STDOUT).decode()

        if "missing" in fsck_output.lower() or "error" in fsck_output.lower():
            print("Possible Git repository corruption:", fsck_output)
            return False

        return True

    except subprocess.CalledProcessError as e:
        print("Git check failed:", e.output.decode())
        return False
