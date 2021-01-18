from click.testing import CliRunner

from jeopardy_data import core


def test_base_cli(PatchedRequests):
    runner = CliRunner()
    result = runner.invoke(core.list_, ["seasons"])

    assert result.exit_code == 0
    assert "1, 2, 3, 4, 5" in result.output

    result = runner.invoke(core.list_, ["games", "--season", "2"])

    assert result.exit_code == 0
    assert "1, 2, 3" in result.output

    result = runner.invoke(core.list_, ["games"])

    assert result.exit_code == 2
    assert "Missing option" in result.output

    result = runner.invoke(core.list_, ["games", "--season"])

    assert result.exit_code == 2
    assert "--season option" in result.output
