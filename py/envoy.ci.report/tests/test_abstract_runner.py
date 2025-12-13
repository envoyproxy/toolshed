
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from aio.run import runner as _runner

from envoy.ci import report


class DummyRunner(report.abstract.AReportRunner):

    @property
    def registered_filters(self):
        return super().registered_filters

    @property
    def registered_formats(self):
        return super().registered_formats

    @property
    def runs_class(self):
        return super().runs_class


def test_runner_constructor():
    with pytest.raises(TypeError):
        report.abstract.AReportRunner()
    runner = DummyRunner()
    assert isinstance(runner, _runner.Runner)

    for fun in "registered_filters", "registered_formats", "runs_class":
        with pytest.raises(NotImplementedError):
            getattr(runner, fun)


def test_runner_filters(patches, iters):
    runner = DummyRunner()
    patched = patches(
        "str",
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.registered_filters",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")
    expected = {}

    def filter_filters(x):
        key = f"K{x}"
        filter = MagicMock()
        filter.return_value.idx = x
        expected[key] = filter
        return (key, filter)

    filters = iters(dict, cb=filter_filters)
    filter_items = filters.items()

    def _str(x):
        if x.idx % 2:
            return f"V{x.idx}"

    with patched as (m_str, m_args, m_filters):
        m_str.side_effect = _str
        m_filters.return_value.items.return_value = filter_items
        assert (
            runner.filters
            == {k: f"V{idx}"
                for idx, k
                in enumerate(expected)
                if idx % 2})

    assert "filters" not in runner.__dict__
    assert (
        m_filters.return_value.items.call_args
        == [(), {}])
    assert (
        m_str.call_args_list
        == [[(x.return_value, ), {}]
            for x in filters.values()])
    for filter in filters.values():
        assert (
            filter.call_args
            == [(m_args.return_value, ), {}])


def test_runner_github(patches):
    runner = DummyRunner()
    patched = patches(
        "_github",
        ("AReportRunner.github_token",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.session",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_github, m_token, m_session):
        assert (
            runner.github
            == m_github.GithubAPI.return_value)

    assert (
        m_github.GithubAPI.call_args
        == [(m_session.return_value, ""),
            dict(oauth_token=m_token.return_value)])


@pytest.mark.parametrize("token_path", [True, False])
def test_runner_github_token(patches, token_path):
    runner = DummyRunner()
    patched = patches(
        "os",
        "pathlib",
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")
    token_path = (MagicMock() if token_path else None)

    with patched as (m_os, m_plib, m_args):
        m_args.return_value.github_token = token_path
        assert (
            runner.github_token
            == ((m_plib.Path.return_value
                       .read_text.return_value
                       .strip.return_value)
                if token_path
                else m_os.getenv.return_value))

    assert "github_token" not in runner.__dict__
    if token_path:
        assert (
            m_plib.Path.call_args
            == [(token_path, ), {}])
        assert (
            m_plib.Path.return_value.read_text.call_args
            == [(), {}])
        assert (
            m_plib.Path.return_value.read_text.return_value.strip.call_args
            == [(), {}])
        assert not m_os.getenv.called
        return
    assert not m_plib.Path.called
    assert (
        m_os.getenv.call_args
        == [(report.abstract.runner.ENV_GITHUB_TOKEN, ), {}])


def test_runner_ignored_triggers(patches):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_args, ):
        assert (
            runner.ignored_triggers
            == m_args.return_value.ignored_triggers.split.return_value)

    assert "ignored_triggers" not in runner.__dict__
    assert (
        m_args.return_value.ignored_triggers.split.call_args
        == [(",", ), {}])


def test_runner_ignored_workflows(patches):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_args, ):
        assert (
            runner.ignored_workflows
            == m_args.return_value.ignored_workflows.split.return_value)

    assert "ignored_workflows" not in runner.__dict__
    assert (
        m_args.return_value.ignored_workflows.split.call_args
        == [(",", ), {}])


@pytest.mark.parametrize("format", [True, False])
def test_runner_format(patches, format):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.registered_formats",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")
    format = (MagicMock() if format else None)

    with patched as (m_args, m_formats):
        m_formats.return_value.get.return_value = format
        if not format:
            with pytest.raises(report.exceptions.CommandError) as e:
                runner.format
        else:
            assert (
                runner.format
                == format.return_value)

    assert (
        m_formats.return_value.get.call_args
        == [(m_args.return_value.format, ), {}])
    if not format:
        assert "format" not in runner.__dict__
        assert (
            e.value.args[0]
            == ("No registered format: "
                f"'{m_args.return_value.format}'"))
        return

    assert "format" in runner.__dict__
    assert (
        format.call_args
        == [(), {}])


def test_runner_repo(patches):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.github",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.repo_name",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_github, m_repo):
        assert (
            runner.repo
            == m_github.return_value.__getitem__.return_value)

    assert "repo" in runner.__dict__
    assert (
        m_github.return_value.__getitem__.call_args
        == [(m_repo.return_value, ), {}])


def test_runner_repo_name(patches):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_args, ):
        assert (
            runner.repo_name
            == m_args.return_value.repo)

    assert "repo_name" not in runner.__dict__


@pytest.mark.parametrize("sort", ["asc", "desc"])
def test_runner_repo_runs(patches, sort):
    runner = DummyRunner()
    patched = patches(
        "dict",
        ("AReportRunner.args",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.filters",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.ignored_triggers",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.ignored_workflows",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.repo",
         dict(new_callable=PropertyMock)),
        ("AReportRunner.runs_class",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as patchy:
        (m_dict, m_args, m_filters,
         m_ign_trig, m_ign_wf, m_repo, m_runs) = patchy
        m_args.return_value.sort = sort
        assert (
            runner.runs
            == m_runs.return_value.return_value)

    assert "runs" in runner.__dict__
    assert (
        m_runs.return_value.call_args
        == [(m_repo.return_value, ),
            dict(filters=m_filters.return_value,
                 ignored=m_dict.return_value,
                 sort_ascending=sort == "asc")])
    assert (
        m_dict.call_args
        == [(),
            dict(workflows=m_ign_wf.return_value,
                 triggers=m_ign_trig.return_value)])


def test_runner_session(patches):
    runner = DummyRunner()
    patched = patches(
        "aiohttp",
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_aiohttp, ):
        assert (
            runner.session
            == m_aiohttp.ClientSession.return_value)

    assert "session" in runner.__dict__
    assert (
        m_aiohttp.ClientSession.call_args
        == [(), {}])


def test_runner_add_arguments(patches):
    runner = DummyRunner()
    parser = MagicMock()
    patched = patches(
        "super",
        ("AReportRunner.registered_formats",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runner")

    with patched as (m_super, m_formats):
        assert not runner.add_arguments(parser)

    assert (
        m_super.call_args
        == [(), {}])
    assert (
        m_super.return_value.add_arguments.call_args
        == [(parser, ), {}])
    assert (
        parser.add_argument.call_args_list
        == [[("--github_token", ), {}],
            [("--repo", ),
             dict(default="envoyproxy/envoy")],
            [("--ignored_triggers", ),
             dict(
                 default=",".join(report.abstract.runner.IGNORED_TRIGGERS))],
            [("--ignored_workflows", ),
             dict(
                 default=",".join(
                     report.abstract.runner.IGNORED_WORKFLOWS))],
            [("-s", "--status"),
             dict(choices=["all", "failure"], default="all")],
            [("--sort", ),
             dict(choices=["asc", "desc"], default="desc")],
            [("-f", "--format"),
             dict(default="json",
                  choices=m_formats.return_value.keys.return_value)]])
    assert (
        parser.add_mutually_exclusive_group.call_args
        == [(), {}])
    assert (
        (parser.add_mutually_exclusive_group.return_value
               .add_argument.call_args_list)
        == [[("--current", ),
             dict(choices=["hour", "day", "week", None],
                  default=None)],
            [("--previous", ),
             dict(choices=["hour", "day", "week", None],
                  default=None)]])


async def test_runner_run(patches):
    runner = DummyRunner()
    patched = patches(
        ("AReportRunner.runs",
         dict(new_callable=PropertyMock)),
        "AReportRunner.format",
        prefix="envoy.ci.report.abstract.runner")
    runs = AsyncMock()

    with patched as (m_runs, m_format):
        m_runs.return_value.as_dict = runs()
        assert not await runner.run()

    assert (
        m_format.call_args
        == [(runs.return_value, ), {}])
