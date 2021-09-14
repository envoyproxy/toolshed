
import configparser
import pathlib
from functools import cached_property
from typing import Dict

from pants.backend.python.goals.setup_py import SetupKwargs
from pants.backend.python.goals.setup_py import SetupKwargsRequest
from pants.engine.rules import rule

from pants.engine.rules import collect_rules
from pants.engine.unions import UnionRule


from . import PytoolingSetupKwargsRequest


class PytoolingSetupKwargsResponse:

    def __init__(self, request: PytoolingSetupKwargsRequest) -> None:
        self.request = request

    @property
    def address(self):
        return self.request.target.address

    @property
    def namespace(self):
        return self.address.spec_path

    @cached_property
    def config(self):
        config = configparser.ConfigParser()
        config.read(f"{self.namespace}/setup.cfg")
        return config

    @property
    def kwargs(self) -> SetupKwargs:
        return SetupKwargs(self.setup_kwargs, address=self.address)  # , _allow_banned_keys=True)

    @property
    def setup_kwargs(self) -> Dict:
        kwargs = self.request.explicit_kwargs.copy()
        for option in self.config["metadata"]:
            kwargs[option] = self.config["metadata"][option]
        kwargs["version"] = self.version
        # kwargs["tags"] = ["setup"]
        return kwargs

    @property
    def version(self) -> str:
        return self.version_file.read_text().strip()

    @property
    def version_file(self) -> pathlib.Path:
        return pathlib.Path(f"{self.namespace}/VERSION")


@rule
async def pytooling_setup_kwargs(
        request: PytoolingSetupKwargsRequest) -> SetupKwargs:
    return PytoolingSetupKwargsResponse(request).kwargs


def rules():
    return (
        *collect_rules(),
        UnionRule(
            SetupKwargsRequest,
            PytoolingSetupKwargsRequest))
