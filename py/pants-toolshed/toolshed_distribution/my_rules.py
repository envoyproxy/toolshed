
import configparser
import pathlib
from functools import cached_property
from typing import Dict

from pants.backend.python.util_rules.package_dists import (
    SetupKwargs, SetupKwargsRequest)
from pants.engine.rules import rule

from pants.engine.rules import collect_rules
from pants.engine.unions import UnionRule


from . import PytoolingSetupKwargsRequest
from toolshed_setup_cfg import (
    parse_entry_points,
    parse_extras_require,
    parse_metadata,
    parse_options,
)


class PytoolingSetupKwargsResponse:

    # Pants forbids the following kwargs in `provides=setup_py(...)` because
    # it derives them from the BUILD graph itself:
    #   data_files, install_requires, namespace_packages,
    #   package_dir, package_data, packages
    # See:
    #   https://www.pantsbuild.org/docs/python-distributions
    #   pants/docs/docs/python/overview/building-distributions.mdx
    #
    # Therefore the corresponding [options]/[options.*] sections of
    # setup.cfg are intentionally NOT propagated by this plugin and exist
    # purely as documentation / setuptools-compatibility. They are:
    #   - [options] install_requires  (use BUILD deps + requirements.in)
    #   - [options] packages / py_modules / [options.packages.find]
    #   - [options.package_data]      (use `resources()` targets)

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
        return SetupKwargs(self.setup_kwargs, address=self.address)

    @property
    def setup_kwargs(self) -> Dict:
        kwargs = self.request.explicit_kwargs.copy()
        kwargs.update(parse_metadata(self.config, self.namespace))
        kwargs["version"] = self.version

        entry_points = parse_entry_points(self.config)
        if entry_points is not None:
            merged = kwargs.get("entry_points", {})
            merged.update(entry_points)
            kwargs["entry_points"] = merged

        # parse_options returns python_requires, install_requires and
        # zip_safe. install_requires is forbidden by pants (see comment
        # at top of class) so strip it here.
        options_kwargs = parse_options(self.config, self.namespace)
        options_kwargs.pop("install_requires", None)
        kwargs.update(options_kwargs)

        extras_require = parse_extras_require(self.config)
        if extras_require is not None:
            kwargs["extras_require"] = extras_require

        return kwargs

    @property
    def version(self) -> str:
        return self.version_file.read_text().strip()

    @property
    def version_file(self) -> pathlib.Path:
        return pathlib.Path(f"{self.namespace}/VERSION")


@rule
async def toolshed_setup_kwargs(
        request: PytoolingSetupKwargsRequest) -> SetupKwargs:
    return PytoolingSetupKwargsResponse(request).kwargs


def rules():
    return (
        *collect_rules(),
        UnionRule(
            SetupKwargsRequest,
            PytoolingSetupKwargsRequest))
