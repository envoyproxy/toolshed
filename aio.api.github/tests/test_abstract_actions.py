
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from aio.api import github


def test_abstract_actions_constructor():
    actions = github.AGithubActions("REPO")
    assert actions.repo == "REPO"
    assert "repo" not in actions.__dict__


def test_abstract_actions_github(patches):
    actions = github.AGithubActions("REPO")
    patched = patches(
        ("AGithubActions.repo",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.actions.actions")

    with patched as (m_repo, ):
        assert actions.github == m_repo.return_value.github

    assert "github" not in actions.__dict__


def test_abstract_actions_workflows(patches):
    actions = github.AGithubActions("REPO")
    patched = patches(
        ("AGithubActions.github",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.actions.actions")

    with patched as (m_gh, ):
        assert (
            actions.workflows
            == m_gh.return_value.workflows_class.return_value)

    assert (
        m_gh.return_value.workflows_class.call_args
        == [(), dict(actions=actions)])
    assert "workflows" in actions.__dict__


def test_abstract_workflows_workflows():
    workflows = github.AGithubWorkflows("ACTIONS")
    assert workflows.actions == "ACTIONS"
    assert "actions" not in workflows.__dict__


def test_abstract_workflows_github(patches):
    workflows = github.AGithubWorkflows("ACTIONS")
    patched = patches(
        ("AGithubWorkflows.actions",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.actions.actions")

    with patched as (m_actions, ):
        assert workflows.github == m_actions.return_value.github

    assert "github" not in workflows.__dict__


def test_abstract_workflows_repo(patches):
    workflows = github.AGithubWorkflows("ACTIONS")
    patched = patches(
        ("AGithubWorkflows.actions",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.actions.actions")

    with patched as (m_actions, ):
        assert workflows.repo == m_actions.return_value.repo

    assert "repo" not in workflows.__dict__


async def test_abstract_workflows_dispatch(patches):
    workflows = github.AGithubWorkflows("ACTIONS")
    patched = patches(
        "get_installation_access_token",
        ("AGithubWorkflows.github",
         dict(new_callable=PropertyMock)),
        ("AGithubWorkflows.repo",
         dict(new_callable=PropertyMock)),
        prefix="aio.api.github.abstract.actions.actions")
    workflow = MagicMock()
    app_id = MagicMock()
    install_id = MagicMock()
    key = MagicMock()
    data = MagicMock()

    with patched as (m_token, m_gh, m_repo):
        m_repo.return_value.post.side_effect = AsyncMock()
        assert not await workflows.dispatch(
            workflow, app_id, install_id, key, data)

    assert (
        m_token.call_args
        == [(m_gh.return_value.api, ),
            dict(installation_id=install_id,
                 app_id=app_id,
                 private_key=key)])
    assert (
        m_repo.return_value.post.call_args
        == [(f"actions/workflows/{workflow}/dispatches", ),
            dict(oauth_token=m_token.return_value.__getitem__.return_value,
                 data=data)])
    assert (
        m_token.return_value.__getitem__.call_args
        == [("token", ), {}])
