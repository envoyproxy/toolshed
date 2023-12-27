
import abc
import pathlib
import re
from functools import cached_property
from typing import Mapping, Type

import abstracts

from aio.core import directory as _directory, event, utils
from aio.run import checker

from dependatool.exceptions import PipConfigurationError


DEPENDABOT_CONFIG = ".github/dependabot.yml"
IGNORED_DIRS = (
    r"^/tools/dev$",
    r"^/tools/dev/src",
    "^/examples/shared/envoy",
    "^/examples/vrp",
    "^/examples/wasm",
    "^/examples/win")

# TODO(phlax): add checks for:
#      - requirements can be installed together
#      - pip-compile formatting


@abstracts.implementer(event.AExecutive)
class ADependatoolChecker(
        checker.Checker,
        metaclass=abstracts.Abstraction):
    checks = ("docker", "gomod", "npm", "pip")
    _config = DEPENDABOT_CONFIG

    @cached_property
    @abstracts.interfacemethod
    def check_tools(self):
        raise NotImplementedError

    @cached_property
    def config(self) -> dict:
        """Parsed dependabot config."""
        result = utils.from_yaml(
            self.path.joinpath(self.config_path))
        if not isinstance(result, dict):
            raise PipConfigurationError(
                "Unable to parse dependabot config: "
                f"{self.config_path}")
        return result

    @property
    def config_path(self) -> str:
        return self._config

    @cached_property
    def directory(self) -> _directory.ADirectory:
        """Greppable directory - optionally in a git repo, depending on whether
        we want to look at all files.
        """
        return self.directory_class(self.path, **self.directory_kwargs)

    @property
    def directory_kwargs(self) -> Mapping:
        return dict(
            pool=self.pool,
            loop=self.loop)

    @property  # type:ignore
    @abstracts.interfacemethod
    def directory_class(self) -> Type[_directory.ADirectory]:
        raise NotImplementedError

    @cached_property
    def ignored_dirs(self) -> re.Pattern:
        return re.compile("|".join(IGNORED_DIRS))

    @property
    @abc.abstractmethod
    def path(self) -> pathlib.Path:
        return super().path

    # TODO: make this public
    async def _run_check(self, check):
        await self.check_tools[check].check()
