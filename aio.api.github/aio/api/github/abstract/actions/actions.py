
from functools import cached_property

import abstracts

from gidgethub.apps import get_installation_access_token

from aio.api.github import interface


@abstracts.implementer(interface.IGithubActions)
class AGithubActions(metaclass=abstracts.Abstraction):
    """Github actions."""

    def __init__(
            self,
            repo: interface.IGithubRepo) -> None:
        self._repo = repo

    @property
    def github(self) -> interface.IGithubAPI:
        return self.repo.github

    @property
    def repo(self) -> interface.IGithubRepo:
        return self._repo

    @cached_property
    def workflows(self) -> "interface.IGithubWorkflows":
        return self.github.workflows_class(actions=self)


@abstracts.implementer(interface.IGithubWorkflows)
class AGithubWorkflows(metaclass=abstracts.Abstraction):
    """Github workflows."""

    def __init__(
            self,
            actions: interface.IGithubActions) -> None:
        self._actions = actions

    @property
    def actions(self) -> interface.IGithubActions:
        return self._actions

    @property
    def github(self) -> interface.IGithubAPI:
        return self.actions.github

    @property
    def repo(self) -> interface.IGithubRepo:
        return self.actions.repo

    async def dispatch(
            self,
            workflow: str,
            app_id: str,
            installation_id: str,
            key: str,
            data: dict = None) -> None:
        access_token_response = await get_installation_access_token(
            self.github.api,
            installation_id=installation_id,
            app_id=app_id,
            private_key=key)
        await self.repo.post(
            f"actions/workflows/{workflow}/dispatches",
            oauth_token=access_token_response["token"],
            data=data)
