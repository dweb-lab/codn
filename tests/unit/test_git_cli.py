import pytest
from typer import Exit

from codn.cli_commands.git_cli import check


@pytest.mark.parametrize(
    "path, is_valid, expected_exit_code",
    [
        (".", True, 0),
        (".", False, 1),
        ("non_existent_path", False, 1),
        ("__file__", False, 1),
    ],
)
def test_check(path, is_valid, expected_exit_code, mocker, capsys):
    """Tests the git check command in different scenarios."""
    mocker.patch(
        "codn.cli_commands.git_cli.git_utils.is_valid_git_repo", return_value=is_valid
    )

    if expected_exit_code != 0:
        with pytest.raises(Exit) as e:
            check(path=path)
        assert e.value.exit_code == expected_exit_code
    else:
        check(path=path)
        captured = capsys.readouterr()
        assert "is a valid Git repository" in captured.out
