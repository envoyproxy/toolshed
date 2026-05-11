"""Sphinx build orchestration for Envoy docs."""

import argparse
import os
import pathlib
import shutil
from functools import cached_property
from typing import TypedDict

from packaging.version import Version

from colorama import Fore, Style  # type:ignore[import-untyped]

from sphinx.cmd.build import (  # type:ignore[import-untyped]
    main as sphinx_build,
)

from aio.run import runner

from envoy.base import utils

from .exceptions import SphinxBuildError, SphinxEnvError


ENVOY_DOCS_BASE_URL = (
    "https://www.envoyproxy.io/docs/envoy")
SPHINX_WARNINGS_TAIL_LINES = 50


class BaseConfigDict(TypedDict):
    version_string: str
    release_level: str
    blob_sha: str
    version_number: str
    docker_image_tag_name: str
    intersphinx_mapping: dict[str, list[str]]


class ConfigDict(BaseConfigDict, total=False):
    validator_path: str
    descriptor_path: str
    skip_validation: str


class SphinxRunner(runner.Runner):
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

    @property
    def build_target(self) -> str:
        """Sphinx build target - `html` by default"""
        return self.args.build_target

    @cached_property
    def colors(self) -> dict[str, str]:
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
            utils.typed(dict, self.configs),
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
            docker_image_tag_name=self.docker_image_tag_name,
            intersphinx_mapping=self.intersphinx_mapping)
        if self.validate_fragments:
            if self.validator_path:
                _configs["validator_path"] = str(self.validator_path)
            if self.descriptor_path:
                _configs["descriptor_path"] = str(self.descriptor_path)
        else:
            _configs["skip_validation"] = "true"
        return _configs

    @property
    def descriptor_path(self) -> pathlib.Path | None:
        """Path to a descriptor file for config validation."""
        return (
            pathlib.Path(self.args.descriptor_path)
            if self.args.descriptor_path
            else None)

    @property
    def docker_image_tag_name(self) -> str:
        """Tag name of current docker image."""
        semver = Version(self.version_number)
        minor = (
            semver.minor - 1
            if (semver.is_devrelease
                and semver.micro == 0)
            else semver.minor)
        return f"v{semver.major}.{minor}-latest"

    @cached_property
    def docs_tag(self) -> str:
        """Tag name - ie named version for this docs build"""
        if self.args.docs_tag:
            return self.args.docs_tag
        return (
            ""
            if self.version_number.endswith("-dev")
            else f"v{self.version_number}")

    @cached_property
    def html_dir(self) -> pathlib.Path:
        """Path to (temporary) directory for outputting html."""
        return self.build_dir.joinpath("generated", "html")

    @property
    def intersphinx_mapping(self) -> dict[str, list[str]]:
        return (
            {f"v{k}": [
                f"{ENVOY_DOCS_BASE_URL}/v{v}",
                f"inventories/v{k}/objects.inv"]
             for k, v
             in utils.from_yaml(self.versions_path, dict[str, str]).items()}
            if self.versions_path.exists()
            else {})

    @property
    def jobs(self) -> str:
        """Number of parallel jobs to run with Sphinx, defaults to `auto`."""
        return self.args.jobs

    @property
    def warnings_file(self) -> pathlib.Path:
        """Path to file Sphinx writes warnings (and errors) to."""
        return self.build_dir.joinpath("sphinx-warnings.txt")

    @property
    def output_path(self) -> pathlib.Path:
        """Path to tar file or directory for saving generated html docs."""
        return pathlib.Path(self.args.output_path)

    @property
    def overwrite(self) -> bool:
        """Overwrite output path if exists."""
        return self.args.overwrite

    @property
    def release_level(self) -> str:
        """Release level.

        `tagged` for versioned releases, `pre-release` otherwise.
        """
        return "tagged" if self.docs_tag else "pre-release"

    @cached_property
    def rst_dir(self) -> pathlib.Path:
        """Populates an rst directory with contents of given rst tar, and
        returns the path to the directory."""
        rst_dir = self.build_dir.joinpath("generated", "rst")
        if self.rst_tar is not None:
            utils.extract(rst_dir, self.rst_tar)
        return rst_dir

    @cached_property
    def rst_tar(self) -> pathlib.Path | None:
        """Path to the rst tarball, or None if not provided."""
        return pathlib.Path(self.args.rst_tar) if self.args.rst_tar else None

    @property
    def sphinx_args(self) -> list[str]:
        """Command args for sphinx."""
        sphinx_args = (
            []
            if self.args.verbosity == "info"
            else ["-q"])
        return sphinx_args + [
            "-W",
            "-w", str(self.warnings_file),
            "-j", self.jobs,
            "--keep-going",
            "--color",
            "-b", self.build_target,
            str(self.rst_dir), str(self.html_dir)]

    @property
    def tarmode(self) -> str:
        """Mode to write tarball in - eg `w` or `w:gz`."""
        return (
            "w:gz"
            if self.output_path.name.endswith(".gz")
            else "w")

    @property
    def validate_fragments(self) -> bool:
        """Validate configuration fragments."""
        return bool(
            self.validator_path
            or self.args.validate_fragments)

    @property
    def validator_path(self) -> pathlib.Path | None:
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
    def versions_path(self) -> pathlib.Path:
        """Path to versions.yaml within the extracted RST directory."""
        return self.rst_dir.joinpath("versions.yaml")

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--build_sha")
        parser.add_argument("--build_target", default="html")
        parser.add_argument("--docs_tag")
        parser.add_argument("-j", "--jobs", default="auto")
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
        if rc := sphinx_build(self.sphinx_args):
            warnings = self._read_warnings()
            message = f"BUILD FAILED (sphinx exit code {rc})"
            if warnings:
                message = f"{message}\n\nSphinx warnings:\n{warnings}"
            raise SphinxBuildError(message)
        if warnings := self._read_warnings():
            self.log.warning(
                f"Sphinx emitted warnings despite successful build "
                f"(see {self.warnings_file})")

    def build_summary(self) -> None:
        self.log.info("")
        self.log.info(
            self._color("#### Sphinx build configs #####################"))
        self.log.info(self._color("###"))
        for k, v in self.configs.items():
            self.log.info(
                f"{self._color('###')} {self._color(str(k), 'key')}: "
                f"{self._color(str(v), 'value')}")
        self.log.info(self._color("###"))
        self.log.info(
            self._color("###############################################"))
        self.log.info("")

    def check_env(self) -> None:
        if not self.configs["release_level"] == "tagged":
            return
        if f"v{self.version_number}" != self.docs_tag:
            raise SphinxEnvError(
                "Given git tag does not match the VERSION file content:"
                f"{self.docs_tag} vs v{self.version_number}")
        minor_version = ".".join(self.docs_tag.split(".")[:-1])
        try:
            version_current = self.rst_dir.joinpath(
                "version_history",
                minor_version,
                f"{self.docs_tag}.rst").read_text()
        except FileNotFoundError as e:
            raise SphinxEnvError(
                "Version history file not found "
                f"for {self.docs_tag}: {e}") from e
        if self.version_number not in version_current:
            raise SphinxEnvError(
                f"Git tag ({self.version_number}) not found in "
                f"version_history/{minor_version}/{self.docs_tag}.rst")

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
        utils.pack(self.html_dir, self.output_path)

    @runner.cleansup
    @runner.catches((SphinxBuildError, SphinxEnvError))
    async def run(self) -> int | None:
        self.validate_args()
        os.environ["ENVOY_DOCS_BUILD_CONFIG"] = str(self.config_file)
        self.check_env()
        self.build_summary()
        self.build_html()
        self.save_html()

    def validate_args(self) -> None:
        if self.output_path.exists():
            if not self.overwrite:
                raise SphinxEnvError(
                    f"Output path ({self.output_path}) exists and "
                    "`--overwrite` is not set`")

    def _color(self, msg: str, name: str | None = None) -> str:
        return f"{self.colors[name or 'chrome']}{msg}{Style.RESET_ALL}"

    def _read_warnings(self) -> str:
        """Read tail of Sphinx warning file, if present and non-empty."""
        warnings_file = self.warnings_file
        if not warnings_file.exists():
            return ""
        warnings = warnings_file.read_text()
        if not warnings.strip():
            return ""
        warnings_lines = warnings.splitlines()
        warnings_tail = "\n".join(warnings_lines[-SPHINX_WARNINGS_TAIL_LINES:])
        if len(warnings_lines) <= SPHINX_WARNINGS_TAIL_LINES:
            return warnings_tail
        return (
            f"...(truncated, full warnings in {warnings_file})\n"
            + warnings_tail)
