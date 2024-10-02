
import types
from functools import partial
from itertools import product
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from envoy.ci import report


@pytest.mark.parametrize("filters", ["FILTERS", None])
@pytest.mark.parametrize("ignored", ["IGNORED", None])
@pytest.mark.parametrize("ascending", [True, False, None])
def test_runs_constructor(filters, ignored, ascending):
    kwargs = {}
    if filters:
        kwargs["filters"] = filters
    if ignored:
        kwargs["ignored"] = ignored
    if ascending is not None:
        kwargs["sort_ascending"] = ascending

    runs = report.abstract.ACIRuns("REPO", **kwargs)
    assert runs.repo == "REPO"
    assert runs.filters == (filters or {})
    assert runs.ignored == (ignored or {})
    assert (
        runs.sort_ascending
        == (ascending
            if ascending is not None
            else False))
    assert "sort_ascending" not in runs.__dict__


async def test_runs_as_dict(patches):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "ACIRuns._sorted",
        "ACIRuns._to_dict",
        prefix="envoy.ci.report.abstract.runs")

    with patched as (m_sorted, m_dict):
        assert (
            await runs.as_dict
            == m_sorted.return_value)

    assert (
        m_sorted.call_args
        == [(m_dict.return_value, ), {}])
    assert (
        m_dict.call_args
        == [(), {}])
    assert not hasattr(runs, "__async_prop_cache__")


async def test_runs_check_runs(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "concurrent",
        ("ACIRuns._check_run_fetches",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")

    def _check_runs(key):
        if key % 2:
            return
        return f"A{key}", f"B{key}", f"C{key}"
    check_runs = iters(cb=_check_runs)
    expected = {}
    for key in check_runs:
        if not key:
            continue
        a, b, c = key
        expected[a] = expected.get(a, {})
        expected[a][b] = expected[a].get(b, [])
        expected[a][b].append(c)

    async def _concurrent(items):
        for run in check_runs:
            yield run

    with patched as (m_concurrent, m_fetch):
        m_concurrent.side_effect = _concurrent
        assert (
            await runs.check_runs
            == expected
            == getattr(
                runs,
                report.abstract.ACIRuns.check_runs.cache_name)["check_runs"])

    assert (
        m_concurrent.call_args
        == [(m_fetch.return_value, ), {}])


async def test_runs_envs(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "concurrent",
        ("ACIRuns._env_fetches",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")

    def _envs(key):
        if key % 2:
            return f"A{key}", (f"B{key}", f"C{key}", f"D{key}")
    envs = iters(cb=_envs)
    expected = {}
    for key in envs:
        if not key:
            continue
        a, (b, c, d) = key
        expected[c] = expected.get(c, {})
        expected[c][d] = expected[c].get(d, {})
        expected[c][d][b] = a

    async def _concurrent(items):
        for run in envs:
            yield run

    with patched as (m_concurrent, m_fetch):
        m_concurrent.side_effect = _concurrent
        assert (
            await runs.envs
            == expected
            == getattr(
                runs,
                report.abstract.ACIRuns.envs.cache_name)["envs"])

    assert (
        m_concurrent.call_args
        == [(m_fetch.return_value, ), {}])


def test_runs_github_headers():
    repo = MagicMock()
    runs = report.abstract.ACIRuns(repo)
    assert (
        runs.github_headers
        == {"Authorization": f"token {repo.github.api.oauth_token}"})
    assert "github_headers" not in runs.__dict__


async def test_runs_shas(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "set",
        ("ACIRuns.workflows",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    wfs = MagicMock()
    wf_values = iters(cb=lambda x: MagicMock())
    wfs.values.return_value = wf_values

    with patched as (m_set, m_wfs):
        m_wfs.return_value = AsyncMock(return_value=wfs)()
        assert (
            await runs.shas
            == getattr(
                runs,
                report.abstract.ACIRuns.shas.cache_name)["shas"]
            == m_set.return_value)
        resultiter = m_set.call_args[0][0]
        resultlist = list(resultiter)

    assert isinstance(resultiter, types.GeneratorType)
    assert (
        resultlist
        == [m.__getitem__.return_value for m in wf_values])
    for wf in wf_values:
        assert (
            wf.__getitem__.call_args
            == [("head_sha", ), {}])


async def test_runs_workflow_requests(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "concurrent",
        ("ACIRuns.shas",
         dict(new_callable=PropertyMock)),
        ("ACIRuns.fetch_requests",
         dict(new_callable=MagicMock)),
        prefix="envoy.ci.report.abstract.runs")

    def _requests(key):
        return iters(
            cb=lambda x: (f"A{key}_{x}", f"B{key}_{x}", f"C{key}_{x}"))

    requests = iters(cb=_requests)
    shas = iters()

    async def _concurrent(items):
        for reqs in requests:
            yield reqs

    expected = {}
    for reqs in requests:
        for request in reqs:
            (sha, event, wfid) = request
            expected[sha] = expected.get(sha, {})
            expected[sha][event] = expected[sha].get(event, [])
            expected[sha][event].append(wfid)

    with patched as (m_concurrent, m_shas, m_fetch):
        m_shas.return_value = AsyncMock(return_value=shas)()
        m_concurrent.side_effect = _concurrent
        assert (
            await runs.workflow_requests
            == getattr(
                runs,
                report.abstract.ACIRuns.workflow_requests.cache_name)[
                    "workflow_requests"]
            == expected)

    assert (
        m_fetch.call_args_list
        == [[(sha, ), {}] for sha in shas])
    assert (
        m_concurrent.call_args
        == [([m_fetch.return_value for sha in shas], ), {}])


@pytest.mark.parametrize("ignored", [True, False])
async def test_runs_workflows(patches, iters, ignored):
    repo = MagicMock()

    def _contains(k):
        return int(k[-1]) % 2
    if ignored:
        ignored = MagicMock()
        ignored.get.return_value.__contains__.side_effect = _contains
    divisor = 1 if not ignored else 2

    runs = report.abstract.ACIRuns(repo, ignored=ignored or None)
    patched = patches(
        "dict",
        ("ACIRuns.workflows_url",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    wfs = iters(cb=lambda x: MagicMock())

    def _getitem(wf, i, k):
        return f"{k}{i}"

    async def _getiter(*args, **kwargs):
        for i, wf in enumerate(wfs):
            wf.__getitem__.side_effect = partial(_getitem, wf, i)
            yield wf

    repo.getiter.side_effect = _getiter

    with patched as (m_dict, m_url):
        expected = {
            f"id{x}": m_dict.return_value
            for x, y in enumerate(wfs)
            if not x % divisor}
        result = await runs.workflows
        assert (
            result
            == expected
            == getattr(
                runs,
                report.abstract.ACIRuns.workflows.cache_name)["workflows"])

    assert (
        repo.getiter.call_args
        == [(m_url.return_value, ), dict(iterable_key="workflow_runs")])
    if ignored:
        assert (
            ignored.get.call_args_list
            == [[("workflows", []), {}]
                for wf in wfs])
        assert (
            ignored.get.return_value.__contains__.call_args_list
            == [[(f"name{i}", ), {}]
                for i, wf in enumerate(wfs)])
    assert (
        m_dict.call_args_list
        == [[(),
             dict(head_sha=f"head_sha{i}",
                  name=f"name{i}",
                  status=f"status{i}",
                  event=f"event{i}",
                  conclusion=f"conclusion{i}")]
            for i, wf in enumerate(wfs)
            if not i % divisor])


@pytest.mark.parametrize("filters", [True, False])
async def test_runs_workflows_url(iters, filters):
    filter_items = {}
    if filters:
        filter_items = iters(dict).items()
        filters = MagicMock()
        filters.items.return_value = filter_items
    runs = report.abstract.ACIRuns("REPO", filters=filters)
    filter_string = "&".join([
        f"{k}={v}"
        for k, v
        in filter_items])
    filter_string = f"&{filter_string}" if filter_string else ""
    assert (
        runs.workflows_url
        == (f"{report.abstract.runs.URL_GH_REPO_ACTIONS}"
            f"{filter_string}"))


@pytest.mark.parametrize("include_workflow", [True, False])
async def test_runs_fetch_check(patches, include_workflow):
    repo = MagicMock()
    repo.getitem = AsyncMock()
    runs = report.abstract.ACIRuns(repo)
    patched = patches(
        "int",
        ("ACIRuns.workflows",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    commit = MagicMock()
    event = MagicMock()
    info = MagicMock()
    _workflows = AsyncMock()
    _workflows.return_value.__contains__.return_value = include_workflow

    with patched as (m_int, m_wfs):
        m_wfs.side_effect = _workflows
        assert (
            await runs.fetch_check(commit, event, info)
            == ((commit, event, info)
                if include_workflow
                else None))

    assert (
        repo.getitem.call_args
        == [(f"check-runs/{info.__getitem__.return_value}", ), {}])
    assert (
        info.__getitem__.call_args
        == [("check-id", ), {}])
    assert (
        m_int.call_args
        == [(repo.getitem.return_value.__getitem__.return_value, ), {}])
    assert (
        repo.getitem.return_value.__getitem__.call_args_list[0]
        == [("external_id", ), {}])
    assert (
        _workflows.return_value.__contains__.call_args
        == [(m_int.return_value, ), {}])
    if not include_workflow:
        assert not info.pop.called
        assert not info.__setitem__.called
        assert (
            len(repo.getitem.return_value.__getitem__.call_args_list)
            == 1)
        return
    assert (
        info.__delitem__.call_args
        == [("action", ), {}])
    assert (
        info.pop.call_args
        == [("advice", None), {}])
    assert (
        info.__setitem__.call_args
        == [("external_id",
             repo.getitem.return_value.__getitem__.return_value), {}])
    assert (
        repo.getitem.return_value.__getitem__.call_args_list[1]
        == [("external_id", ), {}])


@pytest.mark.parametrize("status", [200, 300, 400])
async def test_runs_fetch_request_env(patches, status):
    repo = MagicMock()
    runs = report.abstract.ACIRuns(repo)
    patched = patches(
        "ACIRuns.parse_env",
        "ACIRuns._fetch_env_artifact",
        prefix="envoy.ci.report.abstract.runs")
    wfid = MagicMock()
    sha = MagicMock()
    event = MagicMock()
    response = AsyncMock()
    response.status = status

    with patched as (m_parse, m_fetch):
        m_fetch.return_value.__aenter__.return_value = response
        if status == 200:
            assert (
                await runs.fetch_request_env(wfid, sha, event)
                == (m_parse.return_value, (wfid, sha, event)))
        else:
            error = report.exceptions.RequestArtifactFetchError
            with pytest.raises(error) as e:
                await runs.fetch_request_env(wfid, sha, event)

    assert (
        m_fetch.call_args
        == [(wfid, ), {}])
    if status != 200:
        assert (
            e.value.args[0]
            == f"Failed to download: {status}")
        assert not m_parse.called
        assert not response.read.called
        return
    assert (
        m_parse.call_args
        == [(response.read.return_value, ), {}])
    assert (
        response.read.call_args
        == [(), {}])


@pytest.mark.parametrize("ignored", [True, False])
async def test_runs_fetch_requests(patches, iters, ignored):
    repo = MagicMock()

    def _contains(k):
        return int(k[-1]) % 2
    if ignored:
        ignored = MagicMock()
        ignored.get.return_value.__contains__.side_effect = _contains
    divisor = 1 if not ignored else 2
    runs = report.abstract.ACIRuns(repo, ignored=ignored or None)
    wfs = iters(cb=lambda x: MagicMock())
    sha = MagicMock()

    def _getitem(wf, i, k):
        return f"{k}{i}"

    async def _getiter(*args, **kwargs):
        for i, wf in enumerate(wfs):
            wf.__getitem__.side_effect = partial(_getitem, wf, i)
            yield wf

    repo.getiter.side_effect = _getiter
    assert (
        await runs.fetch_requests(sha)
        == [(sha, f"event{i}", f"id{i}")
            for i, wf in enumerate(wfs)
            if not i % divisor])
    assert (
        repo.getiter.call_args
        == [(report.abstract.runs.URL_GH_REPO_ACTIONS_REQUEST.format(sha=sha),
             ),
            dict(iterable_key="workflow_runs")])
    if not ignored:
        return
    assert (
        ignored.get.call_args_list
        == [[("triggers", []), {}]
            for wf in wfs])
    assert (
        ignored.get.return_value.__contains__.call_args_list
        == [[(f"event{i}", ), {}]
            for i, wf in enumerate(wfs)])


@pytest.mark.parametrize("find_env", [True, False])
def test_runs_parse_env(patches, iters, find_env):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "dict",
        "json",
        "io",
        "zipfile",
        prefix="envoy.ci.report.abstract.runs")
    data = MagicMock()
    infolist = iters(cb=lambda x: MagicMock())
    for i, file in enumerate(infolist):
        if find_env and (i in [2, 4]):
            file.filename = report.abstract.runs.GH_ACTION_REQUEST_FILE

    with patched as (m_dict, m_json, m_io, m_zip):
        (m_zip.ZipFile.return_value.__enter__
              .return_value.infolist.return_value) = infolist
        if find_env:
            assert (
                runs.parse_env(data)
                == m_dict.return_value)
        else:
            error = report.exceptions.RequestArtifactFetchError
            with pytest.raises(error) as e:
                runs.parse_env(data)

    assert (
        m_zip.ZipFile.call_args
        == [(m_io.BytesIO.return_value, ), {}])
    assert (
        m_io.BytesIO.call_args
        == [(data, ), {}])
    assert (
        m_zip.ZipFile.return_value.__enter__.return_value.infolist.call_args
        == [(), {}])
    if not find_env:
        assert (
            not m_zip.ZipFile.return_value.__enter__.return_value.open.called)
        assert not m_json.load.called
        assert not m_dict.called
        assert e.value.args[0] == "Failed to find env.json in download"
        return
    assert (
        m_zip.ZipFile.return_value.__enter__.return_value.open.call_args_list
        == [[(infolist[2], ), {}]])
    assert (
        m_json.load.call_args
        == [((m_zip.ZipFile.return_value.__enter__
                   .return_value.open.return_value.__enter__.return_value), ),
            {}])
    assert (
        m_dict.call_args
        == [(),
            dict(checks=m_json.load.return_value.__getitem__.return_value,
                 request=m_json.load.return_value.__getitem__.return_value)])
    assert (
        m_json.load.return_value.__getitem__.call_args_list
        == [[("checks", ), {}],
            [("request", ), {}]])


async def test_runs__check_run_fetches(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        ("ACIRuns.envs",
         dict(new_callable=PropertyMock)),
        ("ACIRuns.workflow_requests",
         dict(new_callable=PropertyMock)),
        ("ACIRuns.fetch_check",
         dict(new_callable=MagicMock)),
        prefix="envoy.ci.report.abstract.runs")

    _check_runs = []

    def _check(idx):
        check = MagicMock()
        if idx % 2:
            check.__getitem__.return_value = "RUN"
            _check_runs.append(check)
        return f"CHECK{idx}", check

    def _data(idx):
        data = MagicMock()
        data.__getitem__.return_value.items.return_value = iters(
            dict, cb=_check).items()
        return f"DATA{idx}", data

    def _envs(idx):
        env = MagicMock()
        env.items.return_value = iters(dict, cb=_data).items()
        return (f"ENV{idx}", env)

    envs = MagicMock()
    envs.get.return_value.items.return_value = iters(
        dict, cb=_envs).items()
    wfs = MagicMock()
    wfs.items.return_value = iters(
        dict,
        cb=lambda x: (f"WF{x}", MagicMock())).items()

    with patched as (m_envs, m_wf_reqs, m_fetch):
        m_envs.side_effect = AsyncMock(return_value=envs)
        m_wf_reqs.side_effect = AsyncMock(return_value=wfs)
        assert (
            [_result
             async for _result
             in runs._check_run_fetches]
            == [m_fetch.return_value] * (625 - 375))

    assert not hasattr(runs, "__async_prop_cache__")
    assert (
        m_fetch.call_args_list
        == [[(f"WF{idx0}", f"ENV{idx1}", _check_runs[count % 50]), {}]
            for count, (idx0, idx1, idx2, idx3)
            in enumerate(
                (idx0, idx1, idx2, idx3)
                for idx0, idx1, idx2, idx3
                in product(range(5), repeat=4)
                if idx3 % 2)])


async def test_runs__env_fetches(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        ("ACIRuns.fetch_request_env",
         dict(new_callable=MagicMock)),
        ("ACIRuns.workflow_requests",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    _workflows = AsyncMock()
    results = []

    class DummyFetchProvider(object):
        _wfids = []
        _shas = {}

        def _wf_ids(self, k):
            event = MagicMock()
            wfids = iters(cb=lambda x: f"A{k}B{x}")
            self._wfids.extend(wfids)
            return event, wfids

        def _wf_requests(self, k):
            sha = MagicMock()
            events = MagicMock()
            _events = iters(
                dict, cb=self._wf_ids).items()
            events.items = MagicMock(
                return_value=_events)
            self._shas[sha] = _events
            return sha, events

    provider = DummyFetchProvider()

    _workflows.return_value.items = MagicMock(
        return_value=iters(
            dict, cb=provider._wf_requests).items())

    with patched as (m_fetch, m_wfs):
        m_wfs.side_effect = _workflows

        async for fetch_fun in runs._env_fetches:
            results.append(fetch_fun)

    assert not hasattr(runs, "__async_prop_cache__")
    expected = []
    for sha, events in provider._shas.items():
        for event, wfids in events:
            for wfid in wfids:
                expected.append((wfid, sha, event))
    assert (
        results
        == [m_fetch.return_value] * len(provider._wfids))
    assert (
        m_fetch.call_args_list
        == [[expect, {}]
            for expect in expected])


async def test_runs__fetch_env_artifact(patches):
    repo = MagicMock()
    runs = report.abstract.ACIRuns(repo)
    patched = patches(
        ("ACIRuns.github_headers",
         dict(new_callable=PropertyMock)),
        "ACIRuns._resolve_env_artifact_url",
        prefix="envoy.ci.report.abstract.runs")
    wfid = MagicMock()

    with patched as (m_headers, m_url):
        assert (
            await runs._fetch_env_artifact(wfid)
            == repo.github.session.get.return_value)

    assert (
        repo.github.session.get.call_args
        == [(m_url.return_value, ),
            dict(headers=m_headers.return_value)])
    assert (
        m_url.call_args
        == [(wfid, ), {}])


@pytest.mark.parametrize("raises", [Exception, IndexError, None])
async def test_runs__resolve_env_artifact_url(patches, iters, raises):
    repo = AsyncMock()
    runs = report.abstract.ACIRuns(repo)
    wfid = MagicMock()
    patched = patches(
        "log",
        prefix="envoy.ci.report.abstract.runs")
    (repo.getitem.return_value
         .__getitem__.return_value
         .__getitem__.side_effect) = raises

    with patched as (m_log, ):
        if raises == Exception:
            with pytest.raises(Exception):
                await runs._resolve_env_artifact_url(wfid)
        elif raises == IndexError:
            assert not await runs._resolve_env_artifact_url(wfid)
        else:
            assert (
                await runs._resolve_env_artifact_url(wfid)
                == (repo.getitem.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value
                        .__getitem__.return_value))

    assert (
        repo.getitem.call_args
        == [((report.abstract.runs
                    .URL_GH_REPO_ACTION_ENV_ARTIFACT.format(wfid=wfid)), ),
            {}])
    assert (
        repo.getitem.return_value.__getitem__.call_args
        == [("artifacts", ), {}])
    assert (
        (repo.getitem.return_value
             .__getitem__.return_value
             .__getitem__.call_args)
        == [(0, ), {}])
    if raises:
        assert not (
            repo.getitem.return_value
                .__getitem__.return_value
                .__getitem__.return_value
                .__getitem__).called
        if raises == Exception:
            assert not m_log.warning.called
        elif raises == IndexError:
            assert (
                m_log.warning.call_args
                == [(f"Unable to find request artifact: {wfid}", ), {}])
        return
    assert not m_log.warning.called
    assert (
        (repo.getitem.return_value
             .__getitem__.return_value
             .__getitem__.return_value
             .__getitem__.call_args)
        == [("archive_download_url", ), {}])


@pytest.mark.parametrize("ascending", [True, False])
async def test_runs__sorted(patches, iters, ascending):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "dict",
        "max",
        "min",
        "sorted",
        ("ACIRuns.sort_ascending",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    _runs = MagicMock()
    runsdict = iters(dict)
    _runs.items.return_value = runsdict.items()
    item_values = iters(cb=lambda i: MagicMock())
    item = MagicMock()
    item.__getitem__.return_value = item_values

    with patched as (m_dict, m_max, m_min, m_sorted, m_ascending):
        m_ascending.return_value = ascending
        assert (
            runs._sorted(_runs)
            == m_dict.return_value)
        sortiter = m_sorted.call_args[0][0]
        sortlist = list(sortiter)
        sortlambda = m_sorted.call_args_list[0][1]["key"]
        assert (
            sortlambda(item)
            == (m_min.return_value
                if ascending
                else m_max.return_value))
        if ascending:
            assert not m_max.called
            m_sorter = m_min
        else:
            assert not m_min.called
            m_sorter = m_max
        boundaryiter = m_sorter.call_args[0][0]
        boundarylist = list(boundaryiter)

    assert isinstance(sortiter, types.GeneratorType)
    assert isinstance(boundaryiter, types.GeneratorType)
    assert (
        m_dict.call_args
        == [(m_sorted.return_value, ), {}])
    assert (
        m_sorted.call_args_list[0]
        == [(sortiter, ),
            dict(key=sortlambda, reverse=not ascending)])
    assert (
        sortlist
        == [(k, m_sorted.return_value)
            for k in runsdict.keys()])
    assert (
        m_sorter.call_args
        == [(boundaryiter, ), {}])
    assert (
        item.__getitem__.call_args
        == [(1, ), {}])
    assert (
        boundarylist
        == [item.__getitem__.return_value.__getitem__.return_value
            for item in item_values])
    for _item in item_values:
        assert (
            _item.__getitem__.call_args
            == [("request", ), {}])
        assert (
            _item.__getitem__.return_value.__getitem__.call_args
            == [("started", ), {}])
    subsortlambdas = [
        sorter[1]["key"]
        for sorter
        in m_sorted.call_args_list[1:]]
    assert (
        m_sorted.call_args_list[1:]
        == [[(v, ),
             dict(key=subsortlambdas[i],
                  reverse=not ascending)]
            for i, v
            in enumerate(runsdict.values())])
    for sortfun in subsortlambdas:
        event = MagicMock()
        assert (
            sortfun(event)
            == event.__getitem__.return_value.__getitem__.return_value)
        assert (
            event.__getitem__.call_args
            == [("request", ), {}])
        assert (
            event.__getitem__.return_value.__getitem__.call_args
            == [("started", ), {}])


async def test_runs__to_dict(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        ("ACIRuns.workflow_requests",
         dict(new_callable=PropertyMock)),
        "ACIRuns._to_list_request",
        prefix="envoy.ci.report.abstract.runs")
    workflows = iters(dict)
    wf_requests = {}

    async def _list_request(commit, request):
        if int(commit[1]) % 2:
            requests = iters(cb=lambda x: f"{commit}V{x}")
            wf_requests[commit] = requests
            return requests
        return []

    with patched as (m_workflows, m_list):
        m_workflows.side_effect = AsyncMock(return_value=workflows)
        m_list.side_effect = _list_request
        assert (
            await runs._to_dict()
            == wf_requests)

    assert (
        m_list.call_args_list
        == [[(k, v), {}]
            for k, v in workflows.items()])


async def test_runs__to_list_request(patches, iters):
    runs = report.abstract.ACIRuns("REPO")
    patched = patches(
        "int",
        ("ACIRuns.check_runs",
         dict(new_callable=PropertyMock)),
        ("ACIRuns.envs",
         dict(new_callable=PropertyMock)),
        ("ACIRuns.workflows",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.runs")
    commit = MagicMock()
    request = MagicMock()
    request.items.return_value = iters(
        dict,
        cb=lambda x: (f"REQ{x}", iters(cb=lambda y: MagicMock()))).items()
    expected = []
    workflows = MagicMock()
    check_runs = MagicMock()
    check_runs.get.return_value.get.return_value = iters(
        cb=lambda x: MagicMock())
    envs = MagicMock()

    expected = []
    for _event, _requests in request.items.return_value:
        for _check_run in check_runs.get.return_value.get.return_value:
            for _req in _requests:
                expected.append(
                    {"event": _event,
                     "request": (
                         envs.__getitem__.return_value
                             .__getitem__.return_value
                             .__getitem__.return_value
                             .__getitem__.return_value),
                     "request_id": _req,
                     "check_name": _check_run.__getitem__.return_value,
                     "workflow_id": _check_run.__getitem__.return_value,
                     "workflow": workflows.__getitem__.return_value})

    with patched as (m_int, m_checks, m_envs, m_workflows):
        m_checks.side_effect = AsyncMock(return_value=check_runs)
        m_workflows.side_effect = AsyncMock(return_value=workflows)
        m_envs.side_effect = AsyncMock(return_value=envs)
        assert (
            await runs._to_list_request(commit, request)
            == expected)

    assert (
        envs.__getitem__.call_args_list
        == ([[(commit, ), {}]] * 125))
    assert (
        envs.__getitem__.return_value.__getitem__.call_args_list
        == [[(event, ), {}]
            for event
            in [x[0]
                for x in request.items.return_value
                for _ in range(25)]])
    assert (
        (envs.__getitem__.return_value
             .__getitem__.return_value
             .__getitem__.call_args_list)
        == [[(req, ), {}]
            for _, reqs in request.items.return_value
            for _ in range(5)
            for req in reqs])
    assert (
        (envs.__getitem__.return_value
             .__getitem__.return_value
             .__getitem__.return_value
             .__getitem__.call_args_list)
        == ([[("request", ), {}]] * 125))
    assert (
        check_runs.get.call_args_list
        == [[(commit, {}), {}]] * 5)
    assert (
        check_runs.get.return_value.get.call_args_list
        == [[(req, []), {}]
            for req
            in [x[0]
                for x in request.items.return_value]])
    assert (
        request.items.call_args_list
        == [[(), {}]])
    assert (
        workflows.__getitem__.call_args_list
        == ([[(m_int.return_value, ), {}]] * 125))
    assert (
        m_int.call_args_list
        == [[(c, ), {}]
            for c
            in [check.__getitem__.return_value
                for check
                in check_runs.get.return_value.get.return_value
                for _ in range(5)] * 5])
    for _check_runs in check_runs.get.return_value.get.return_value:
        assert (
            _check_runs.__getitem__.call_args_list
            == [[(k, ), {}]
                for k in ["name", "external_id", "external_id"] * 25])
