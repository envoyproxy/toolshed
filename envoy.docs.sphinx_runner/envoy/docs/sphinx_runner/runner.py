import argparse
import os
import pathlib
import platform
import re
import shutil
import sys
import tarfile
from functools import cached_property
from typing import Dict, List, Optional, TypedDict

from colorama import Fore, Style  # type:ignore

from sphinx.cmd.build import main as sphinx_build  # type:ignore

from aio.run import runner

from envoy.base import utils

from .exceptions import SphinxBuildError, SphinxEnvError


class BaseConfigDict(TypedDict):
    version_string: str
    release_level: str
    blob_sha: str
    version_number: str
    docker_image_tag_name: str


class ConfigDict(BaseConfigDict, total=False):
    validator_path: str
    descriptor_path: str
    skip_validation: str
    intersphinx_mapping: Dict[str, List[str]]


class SphinxRunner(runner.Runner):
    _build_dir = "."
    _build_sha = "UNKNOWN"

    @property
    def blob_sha(self) -> str:
        """Returns either the version tag or the current build sha."""
        return self.docs_tag or self.build_sha

    @property
    def build_dir(self) -> pathlib.Path:
        """Returns current build_dir - most likely a temp directory"""
        return pathlib.Path(self.tempdir.name)

    @property
    def build_sha(self) -> str:
        """Returns either a provided build_sha or a default."""
        return self.args.build_sha or self._build_sha

    @cached_property
    def colors(self) -> dict:
        """Color scheme for build summary."""
        return dict(
            chrome=Fore.LIGHTYELLOW_EX,
            key=Fore.LIGHTCYAN_EX,
            value=Fore.LIGHTMAGENTA_EX)

    @cached_property
    def config_file(self) -> pathlib.Path:
        """Populates a config file with self.configs and returns the file
        path."""
        return utils.to_yaml(
            utils.typed(Dict, self.configs),
            self.config_file_path)

    @property
    def config_file_path(self) -> pathlib.Path:
        """Path to a (temporary) build config."""
        return self.build_dir.joinpath("build.yaml")

    @cached_property
    def configs(self) -> ConfigDict:
        """Build configs derived from provided args."""
        _configs: ConfigDict = dict(
            version_string=self.version_string,
            release_level=self.release_level,
            blob_sha=self.blob_sha,
            version_number=self.version_number,
            docker_image_tag_name=self.docker_image_tag_name)
        if self.validate_fragments:
            if self.validator_path:
                _configs["validator_path"] = str(self.validator_path)
            if self.descriptor_path:
                _configs["descriptor_path"] = str(self.descriptor_path)
        else:
            _configs["skip_validation"] = "true"
        _configs["intersphinx_mapping"] = self.intersphinx_mapping
        return _configs

    @property
    def descriptor_path(self) -> Optional[pathlib.Path]:
        """Path to a descriptor file for config validation."""
        return (
            pathlib.Path(self.args.descriptor_path)
            if self.args.descriptor_path
            else None)

    @property
    def docker_image_tag_name(self) -> str:
        """Tag name of current docker image."""
        return re.sub(
            r"([0-9]+\.[0-9]+)\.[0-9]+.*",
            r"v\1-latest",
            self.version_number)

    @property
    def docs_tag(self) -> str:
        """Tag name - ie named version for this docs build"""
        return self.args.docs_tag

    @cached_property
    def html_dir(self) -> pathlib.Path:
        """Path to (temporary) directory for outputting html."""
        return self.build_dir.joinpath("generated", "html")

    @property
    def intersphinx_mapping(self) -> Dict[str, List[str]]:
        return (
            {f"v{k}": [
                f"https://www.envoyproxy.io/docs/envoy/v{v}",
                f"inventories/v{k}/objects.inv"]
             for k, v
             in utils.from_yaml(self.versions_path, Dict[str, str]).items()}
            if self.versions_path.exists()
            else {})

    @property
    def output_path(self) -> pathlib.Path:
        """Path to tar file or directory for saving generated html docs."""
        return pathlib.Path(self.args.output_path)

    @property
    def overwrite(self) -> bool:
        """Overwrite output path if exists."""
        return self.args.overwrite

    @property
    def py_compatible(self) -> bool:
        """Current python version is compatible."""
        return bool(
            sys.version_info.major == 3
            and sys.version_info.minor >= 8)

    @property
    def release_level(self) -> str:
        """Current python version is compatible."""
        return "tagged" if self.docs_tag else "pre-release"

    @cached_property
    def rst_dir(self) -> pathlib.Path:
        """Populates an rst directory with contents of given rst tar, and
        returns the path to the directory."""
        rst_dir = self.build_dir.joinpath("generated", "rst")
        if self.rst_tar:
            utils.extract(rst_dir, self.rst_tar)
        return rst_dir

    @property
    def rst_tar(self) -> pathlib.Path:
        """Path to the rst tarball."""
        return pathlib.Path(self.args.rst_tar)

    @property
    def sphinx_args(self) -> List[str]:
        """Command args for sphinx."""
        sphinx_args = (
            []
            if self.args.verbosity == "info"
            else ["-q"])
        return sphinx_args + [
            "-W",
            "-j", "auto",
            "--keep-going",
            "--color",
            "-b", "html",
            str(self.rst_dir), str(self.html_dir)]

    @property
    def validate_fragments(self) -> bool:
        """Validate configuration fragments."""
        return bool(
            self.validator_path
            or self.args.validate_fragments)

    @property
    def validator_path(self) -> Optional[pathlib.Path]:
        """Path to validator utility for validating snippets."""
        return (
            pathlib.Path(self.args.validator_path)
            if self.args.validator_path
            else None)

    @property
    def version_file(self) -> pathlib.Path:
        """Path to version files for deriving docs version."""
        return pathlib.Path(self.args.version_file)

    @cached_property
    def version_number(self) -> str:
        """Semantic version."""
        return (
            self.args.version
            if self.args.version
            else self.version_file.read_text().strip())

    @property
    def version_string(self) -> str:
        """Version string derived from either docs_tag or build_sha."""
        return (
            f"tag-{self.docs_tag}"
            if self.docs_tag
            else f"{self.version_number}-{self.build_sha[:6]}")

    @cached_property
    def versions_path(self):
        return self.rst_dir.joinpath("versions.yaml")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--build_sha")
        parser.add_argument("--docs_tag")
        parser.add_argument("--version_file")
        parser.add_argument("--validator_path")
        parser.add_argument("--descriptor_path")
        parser.add_argument("--version")
        parser.add_argument(
            "--validate_fragments", default=False, action="store_true")
        parser.add_argument(
            "--overwrite", default=False, action="store_true")
        parser.add_argument("rst_tar")
        parser.add_argument("output_path")

    def build_html(self) -> None:
        if sphinx_build(self.sphinx_args):
            raise SphinxBuildError("BUILD FAILED")

    def build_summary(self) -> None:
        print()
        print(self._color("#### Sphinx build configs #####################"))
        print(self._color("###"))
        for k, v in self.configs.items():
            print(
                f"{self._color('###')} {self._color(k, 'key')}: "
                f"{self._color(v, 'value')}")
        print(self._color("###"))
        print(self._color("###############################################"))
        print()

    def check_env(self) -> None:
        if not self.py_compatible:
            raise SphinxEnvError(
                "ERROR: python version must be >= 3.8, "
                f"you have {platform.python_version()}")
        if not self.configs["release_level"] == "tagged":
            return
        if f"v{self.version_number}" != self.docs_tag:
            raise SphinxEnvError(
                "Given git tag does not match the VERSION file content:"
                f"{self.docs_tag} vs v{self.version_number}")
        # this should probs only check the first line
        version_current = self.rst_dir.joinpath(
            "version_history", "current.rst").read_text()
        if self.version_number not in version_current:
            raise SphinxEnvError(
                f"Git tag ({self.version_number}) not found in "
                "version_history/current.rst")

    def save_html(self) -> None:
        if self.output_path.exists():
            self.log.warning(
                f"Output path ({self.output_path}) exists, removing")
            if self.output_path.is_file():
                self.output_path.unlink()
            else:
                shutil.rmtree(self.output_path)
        if not utils.is_tarlike(self.output_path):
            shutil.copytree(self.html_dir, self.output_path)
            return
        with tarfile.open(self.output_path, "w") as tar:
            tar.add(self.html_dir, arcname=".")

    @runner.cleansup
    @runner.catches((SphinxBuildError, SphinxEnvError))
    async def run(self):
        self.validate_args()
        os.environ["ENVOY_DOCS_BUILD_CONFIG"] = str(self.config_file)
        try:
            self.check_env()
        except SphinxEnvError as e:
            print(e)
            return 1
        self.build_summary()
        try:
            self.build_html()
        except SphinxBuildError as e:
            print(e)
            return 1
        self.save_html()

    def validate_args(self):
        if self.output_path.exists():
            if not self.overwrite:
                raise SphinxBuildError(
                    f"Output path ({self.output_path}) exists and "
                    "`--overwrite` is not set`")

    def _color(self, msg, name=None):
        return f"{self.colors[name or 'chrome']}{msg}{Style.RESET_ALL}"
