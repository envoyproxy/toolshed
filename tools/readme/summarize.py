
import argparse
import configparser
import pathlib
import sys
from functools import cached_property

import pkg_resources

import packaging.version

import jinja2

from envoy.base import runner


PYPI_PROJECT_URL = "https://pypi.org/project"


class Requirement:

    def __init__(self, req):
        self.req = req

    def __str__(self):
        return f"[{self.name}]({self.pypi_url}) {self.specifier}".strip()

    @property
    def name(self):
        return self.requirement.name

    @property
    def pypi_project_url(self):
        return PYPI_PROJECT_URL

    @property
    def requirement(self):
        return pkg_resources.Requirement.parse(self.req)

    @property
    def specifier(self):
        return self.requirement.specifier

    @property
    def pypi_url(self):
        return f"{self.pypi_project_url}/{self.name}"


class Package:

    def __init__(self, path):
        self.path = path

    @property
    def config(self):
        config = configparser.ConfigParser()
        config.read(self.setup_cfg)
        return config

    @property
    def metadata(self):
        return {
            k: v
            for k, v in self.config["metadata"].items()}

    @property
    def options(self):
        return {
            k: v
            for k, v in self.config["options"].items()}

    @property
    def pypi_project_url(self):
        return PYPI_PROJECT_URL

    @cached_property
    def name(self):
        return self.metadata["name"]

    @property
    def pypi_url(self):
        return f"{self.pypi_project_url}/{self.name}"

    @cached_property
    def requires(self):
        return [
            Requirement(req)
            for req
            in sorted(
                self.options.get("install_requires").strip().split("\n"))]

    @property
    def info(self):
        return dict(metadata=self.metadata)

    @property
    def version(self):
        return packaging.version.Version(self.version_file.read_text().strip())

    @property
    def setup_cfg(self):
        return self.path.joinpath("setup.cfg")

    @property
    def version_file(self):
        return self.path.joinpath("VERSION")


class ReadmePackageRunner(runner.Runner):

    @cached_property
    def template(self):
        return jinja2.Template(pathlib.Path(self.args.template).read_text())

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("template")
        parser.add_argument("path")

    @cached_property
    def package_path(self):
        return pathlib.Path(self.args.path)

    def run(self):
        package = Package(self.package_path)
        print(self.template.render(package=package))


def main(*args):
    return ReadmePackageRunner(*args)()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
