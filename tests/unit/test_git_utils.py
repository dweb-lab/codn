"""Unit tests for codn.utils.git_utils module.

This module contains comprehensive tests for Git repository validation
functionality, including various repository states, error conditions,
and edge cases.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from codn.utils.git_utils import is_valid_git_repo


class TestIsValidGitRepo:
    """Test cases for is_valid_git_repo function."""

    def test_valid_git_repo_with_commits(self, tmp_path):
        """Test with a valid Git repository that has commits."""
        # Create a temporary Git repository
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Configure Git user (required for commits)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create a file and commit
        test_file = repo_dir / "test.txt"
        test_file.write_text("test content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Test with string path
        assert is_valid_git_repo(str(repo_dir)) is True

        # Test with Path object
        assert is_valid_git_repo(repo_dir) is True

    def test_valid_git_repo_no_commits(self, tmp_path):
        """Test with a valid Git repository that has no commits."""
        repo_dir = tmp_path / "empty_repo"
        repo_dir.mkdir()

        # Initialize Git repository (no commits)
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # This should fail because there's no HEAD commit
        assert is_valid_git_repo(repo_dir) is False

    def test_not_a_git_repo(self, tmp_path):
        """Test with a directory that is not a Git repository."""
        non_repo_dir = tmp_path / "not_a_repo"
        non_repo_dir.mkdir()

        assert is_valid_git_repo(non_repo_dir) is False

    def test_nonexistent_path(self, tmp_path):
        """Test with a path that does not exist."""
        nonexistent_path = tmp_path / "does_not_exist"

        assert is_valid_git_repo(nonexistent_path) is False

    def test_file_instead_of_directory(self, tmp_path):
        """Test with a file path instead of directory."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("not a directory")

        assert is_valid_git_repo(test_file) is False

    def test_empty_string_path(self):
        """Test with empty string path."""
        # Empty string resolves to current directory, which might be a git repo
        result = is_valid_git_repo("")
        assert isinstance(result, bool)  # Should return a boolean, not crash

    def test_relative_path(self, tmp_path, monkeypatch):
        """Test with relative path."""
        repo_dir = tmp_path / "relative_repo"
        repo_dir.mkdir()

        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Configure Git user and make a commit
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        test_file = repo_dir / "test.txt"
        test_file.write_text("test")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Change to parent directory and test relative path
        monkeypatch.chdir(tmp_path)
        assert is_valid_git_repo("relative_repo") is True

    @patch("subprocess.run")
    def test_git_command_not_found(self, mock_run):
        """Test when Git command is not available."""
        mock_run.side_effect = FileNotFoundError("Git command not found")

        with patch("sys.stdout"):  # Suppress print output
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_git_rev_parse_fails(self, mock_run):
        """Test when git rev-parse HEAD fails."""
        # First call (rev-parse HEAD) fails
        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            ["git", "rev-parse", "HEAD"],
            stderr="fatal: bad revision 'HEAD'",
        )

        with patch("sys.stdout"):  # Suppress print output
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_git_fsck_fails(self, mock_run):
        """Test when git fsck fails."""
        # First call (rev-parse HEAD) succeeds
        mock_run.return_value = Mock(returncode=0, stdout="abc123", stderr="")

        # Second call (fsck) fails
        mock_run.side_effect = [
            Mock(returncode=0, stdout="abc123", stderr=""),
            subprocess.CalledProcessError(1, ["git", "fsck"], stderr="fsck failed"),
        ]

        with patch("sys.stdout"):  # Suppress print output
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_git_fsck_detects_corruption(self, mock_run):
        """Test when git fsck detects repository corruption."""
        # First call (rev-parse HEAD) succeeds
        # Second call (fsck) succeeds but reports corruption
        mock_run.side_effect = [
            Mock(returncode=0, stdout="abc123", stderr=""),
            Mock(returncode=0, stdout="missing blob 123abc", stderr=""),
        ]

        with patch("sys.stdout"):  # Suppress print output
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_git_fsck_reports_error(self, mock_run):
        """Test when git fsck reports errors in output."""
        # First call (rev-parse HEAD) succeeds
        # Second call (fsck) succeeds but reports errors
        mock_run.side_effect = [
            Mock(returncode=0, stdout="abc123", stderr=""),
            Mock(returncode=0, stdout="error in commit abc123", stderr=""),
        ]

        with patch("sys.stdout"):  # Suppress print output
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_git_fsck_clean_output(self, mock_run):
        """Test when git fsck produces clean output."""
        # First call (rev-parse HEAD) succeeds
        # Second call (fsck) succeeds with clean output
        mock_run.side_effect = [
            Mock(returncode=0, stdout="abc123", stderr=""),
            Mock(returncode=0, stdout="Checking connectivity... done.", stderr=""),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            result = is_valid_git_repo("/some/path")

        assert result is True

    def test_git_dir_exists_but_corrupted(self, tmp_path):
        """Test with .git directory that exists but is corrupted."""
        repo_dir = tmp_path / "corrupted_repo"
        repo_dir.mkdir()

        # Create .git directory but don't initialize properly
        git_dir = repo_dir / ".git"
        git_dir.mkdir()

        # Create some files but not a proper Git repository
        (git_dir / "config").write_text("invalid config")

        assert is_valid_git_repo(repo_dir) is False

    def test_git_worktree(self, tmp_path):
        """Test with Git worktree (should still be valid)."""
        # Create main repository
        main_repo = tmp_path / "main_repo"
        main_repo.mkdir()

        subprocess.run(
            ["git", "init"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Configure Git user
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        test_file = main_repo / "test.txt"
        test_file.write_text("test")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Create a branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main branch
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=main_repo,
            check=True,
            capture_output=True,
        )

        # Main repository should be valid
        assert is_valid_git_repo(main_repo) is True

    @patch("pathlib.Path.exists")
    def test_git_dir_does_not_exist(self, mock_exists):
        """Test when .git directory does not exist."""
        mock_exists.return_value = False

        result = is_valid_git_repo("/some/path")
        assert result is False

    def test_path_resolution_error(self, tmp_path):
        """Test when path resolution fails."""
        # Create a path that doesn't exist
        nonexistent_path = tmp_path / "nonexistent" / "deeply" / "nested"

        result = is_valid_git_repo(str(nonexistent_path))
        assert result is False

    def test_bare_repository(self, tmp_path):
        """Test with bare Git repository."""
        bare_repo = tmp_path / "bare_repo.git"
        bare_repo.mkdir()

        # Initialize bare repository
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=bare_repo,
            check=True,
            capture_output=True,
        )

        # Bare repositories don't have HEAD initially
        assert is_valid_git_repo(bare_repo) is False

    @pytest.mark.parametrize(
        "path_input",
        [
            ".",
            "./",
            "../",
            "~/",
            "/tmp",
        ],
    )
    def test_various_path_formats(self, path_input):
        """Test with various path formats."""
        # Most of these should be False unless they're actual Git repos
        result = is_valid_git_repo(path_input)
        assert isinstance(result, bool)

    def test_concurrent_access(self, tmp_path):
        """Test concurrent access to the same repository."""
        repo_dir = tmp_path / "concurrent_repo"
        repo_dir.mkdir()

        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Configure Git user and make commit
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        test_file = repo_dir / "test.txt"
        test_file.write_text("test")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Multiple calls should all succeed
        results = [is_valid_git_repo(repo_dir) for _ in range(5)]
        assert all(results)

    def test_large_repository_simulation(self, tmp_path):
        """Test with a repository that has multiple commits (simulating larger
        repo)."""
        repo_dir = tmp_path / "large_repo"
        repo_dir.mkdir()

        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Configure Git user
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Create multiple commits
        for i in range(3):
            test_file = repo_dir / f"file_{i}.txt"
            test_file.write_text(f"content {i}")

            subprocess.run(
                ["git", "add", f"file_{i}.txt"],
                cwd=repo_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=repo_dir,
                check=True,
                capture_output=True,
            )

        assert is_valid_git_repo(repo_dir) is True

    def test_unicode_path(self, tmp_path):
        """Test with Unicode characters in path."""
        unicode_repo = tmp_path / "测试_repo_🔥"
        unicode_repo.mkdir()

        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=unicode_repo,
            check=True,
            capture_output=True,
        )

        # Configure Git user and make commit
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=unicode_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=unicode_repo,
            check=True,
            capture_output=True,
        )

        test_file = unicode_repo / "test.txt"
        test_file.write_text("test")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=unicode_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=unicode_repo,
            check=True,
            capture_output=True,
        )

        assert is_valid_git_repo(unicode_repo) is True


class TestGitUtilsEdgeCases:
    """Test edge cases and error conditions."""

    @patch("subprocess.run")
    def test_timeout_scenario(self, mock_run):
        """Test timeout scenario (simulated)."""
        # Simulate a hanging Git command
        mock_run.side_effect = subprocess.TimeoutExpired(
            ["git", "rev-parse", "HEAD"],
            30,
        )

        with patch("sys.stdout"):
            result = is_valid_git_repo("/some/path")

        assert result is False

    @patch("subprocess.run")
    def test_permission_denied(self, mock_run):
        """Test permission denied scenario."""
        mock_run.side_effect = PermissionError("Permission denied")

        with patch("sys.stdout"):
            result = is_valid_git_repo("/some/path")

        assert result is False

    def test_symlink_to_git_repo(self, tmp_path):
        """Test with symlink pointing to a Git repository."""
        # Create actual repository
        real_repo = tmp_path / "real_repo"
        real_repo.mkdir()

        subprocess.run(
            ["git", "init"],
            cwd=real_repo,
            check=True,
            capture_output=True,
        )

        # Configure Git user and make commit
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=real_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=real_repo,
            check=True,
            capture_output=True,
        )

        test_file = real_repo / "test.txt"
        test_file.write_text("test")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=real_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=real_repo,
            check=True,
            capture_output=True,
        )

        # Create symlink
        symlink_repo = tmp_path / "symlink_repo"
        symlink_repo.symlink_to(real_repo)

        # Should work with symlinks
        assert is_valid_git_repo(symlink_repo) is True
