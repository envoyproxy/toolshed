
import difflib
import os
import pathlib
import re
import subprocess
import tempfile
from functools import cached_property, partial
from typing import (
    Callable, Mapping, Pattern, Sequence)

import abstracts

from aio.core.functional import async_property
from aio.core import subprocess as _subprocess
from aio.core import tasks
from aio.run import checker

from envoy.code.check import abstract, exceptions, interface, shared, typing

RE_BAZEL_MATCH = (
    "^WORKSPACE$",
    r"[\w/]*/BUILD$",
    r"[\w/]*.bzl$", )

# Match an Envoy rule, e.g. envoy_cc_library( in a BUILD file.
RE_ENVOY_RULE = r'envoy[_\w]+\('

# Match a load() statement for the envoy_package macros.
RE_PACKAGE_LOAD_BLOCK = r'("envoy_package".*?\)\n)'
RE_EXTENSION_PACKAGE_LOAD_BLOCK = r'("envoy_extension_package".*?\)\n)'
RE_CONTRIB_PACKAGE_LOAD_BLOCK = r'("envoy_contrib_package".*?\)\n)'
RE_MOBILE_PACKAGE_LOAD_BLOCK = r'("envoy_mobile_package".*?\)\n)'

# Canonical Envoy license.
LICENSE_STRING = 'licenses(["notice"])  # Apache 2\n\n'

# Match any existing licenses in a BUILD file.
RE_OLD_LICENSES = r'^licenses\(.*\n+'

# Match Buildozer 'print' output. Example of Buildozer print output:
# cc_library json_transcoder_filter_lib
# [json_transcoder_filter.cc] (missing) (missing)
RE_BUILDOZER_PRINT = (
    r"\s*([\w_]+)\s+([\w_]+)\s+"
    r"[(\[](.*?)[)\]]\s+[(\[](.*?)[)\]]\s+[(\[](.*?)[)\]]")

# Match API header include in Envoy source file?
RE_API_INCLUDE = (
    r'#include "(contrib/envoy/.*|envoy/.*)/[^/]+\.pb\.(validate\.)?h"')

XDS_PKG_PROTO = "@com_github_cncf_xds//udpa/annotations:pkg_cc_proto"


class EnvoyBuildozer(object):

    def __init__(self, buildozer_path, filepath):
        self.buildozer_path = buildozer_path
        self.filepath = filepath

    @cached_property
    def re_api_include(self) -> Pattern[str]:
        """Regex to match files to check."""
        return re.compile(RE_API_INCLUDE)

    @cached_property
    def re_print(self) -> Pattern[str]:
        return re.compile(RE_BUILDOZER_PRINT)

    # Run Buildozer commands on a string representing a BUILD file.
    def run(self, cmds: list[tuple[str, str]], text: str) -> str:
        with tempfile.NamedTemporaryFile(mode='w') as cmd_file:
            # We send the BUILD contents to buildozer on stdin and receive the
            # transformed BUILD on stdout. The commands are provided in a file.
            cmd_path = pathlib.Path(cmd_file.name)
            cmd_path.write_text(
                '\n'.join(
                    '%s|-:%s'
                    % (cmd, target) for cmd, target in cmds))
            return self._run(cmd_path, text).strip()

    def _run(self, cmd_path: pathlib.Path, text: str) -> str:
        response = subprocess.run(
            [self.buildozer_path, '-stdout', '-f', str(cmd_path)],
            input=text.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        # Buildozer uses 3 for success but no change
        # (0 is success and changed).
        if response.returncode not in [0, 3]:
            raise exceptions.FixError(
                f"buildozer execution failed: {response}")
        # Sometimes buildozer feels like returning nothing when the
        # transform is a nop.
        return (
            response.stdout.decode()
            if response.stdout
            else text)

    def mutation_cmds(self, text: str) -> list[tuple[str, str]]:
        buildozer_out = self.run(
            [('print kind name srcs hdrs deps', '*')],
            text).split('\n')
        return [
            cmd
            for line
            in buildozer_out
            if (match := self.re_print.match(line))
            for cmd
            in self.mutations(match)]

    def mutations(self, match) -> list[tuple[str, str]]:
        mutations = []
        kind, name, srcs, hdrs, deps = match.groups()
        if kind == "envoy_pch_library" or not name:
            return []
        actual_api_deps = self.api_deps_actual(srcs, hdrs)
        existing_api_deps = self.api_deps(deps)
        deps_to_add = actual_api_deps - existing_api_deps
        deps_to_remove = existing_api_deps - actual_api_deps
        if deps_to_add:
            mutations.append(
                (f"add deps {' '.join(deps_to_add)}", name))
        if deps_to_remove:
            mutations.append(
                (f"remove deps {' '.join(deps_to_remove)}",
                 name))
        return mutations

    def api_deps(self, deps: str) -> set[str]:
        return {
            dep
            for dep
            in (deps if deps != "missing" else "").split()
            if (dep.startswith("@envoy_api")
                and dep.endswith("pkg_cc_proto")
                and dep != XDS_PKG_PROTO)}

    def api_deps_actual(self, srcs: str, hdrs: str) -> set[str]:
        return {
            dep
            for path
            in self.source_paths(srcs, hdrs)
            for dep
            in self.find_api_deps(path)}

    def dep_files(
            self,
            files: str,
            endswith: str | tuple) -> list[str]:
        return [
            self.filepath.parent.joinpath(filename)
            for filename
            in (files if files != "missing" else "").split()
            if filename.endswith(endswith)]

    # Find all the API headers in a C++ source file.
    def find_api_deps(self, path: pathlib.Path) -> set[str]:
        if not path.exists():
            return set()
        with path.open() as fd:
            return set(
                f"@envoy_api//{match.group(1)}:pkg_cc_proto"
                for line in fd
                if (match := self.re_api_include.match(line)))

    def source_paths(self, srcs, hdrs):
        filenames = set()
        for filename in self.dep_files(srcs, (".cc", ".h")):
            filenames.add(filename)
            yield filename
        for filename in self.dep_files(hdrs, ".h"):
            if filename not in filenames:
                yield filename


@abstracts.implementer(_subprocess.ISubprocessHandler)
class EnvoyBuildifier(_subprocess.ASubprocessHandler):
    api_prefix: str = "api"
    _diff_output: str | None = None

    def __init__(self, *args, **kwargs) -> None:
        self.config: typing.YAMLConfigDict = kwargs.pop("config")
        self.filepath = kwargs.pop("filepath")
        self.buildozer_path = kwargs.pop("buildozer_path")
        super().__init__(*args, **kwargs)

    @cached_property
    def allowed_bazel_tools(self) -> bool:
        return (
            self.is_starlark
            or (not self.is_mobile
                and self.filepath.parts[0] == "bazel")
            or (self.is_mobile
                and self.filepath.parts[1] == "bazel"))

    @cached_property
    def allowed_protobuf_direct(self):
        return (
            self.filepath.name.endswith(
                (*self.format_config.suffixes["proto"],
                 *self.format_config.suffixes["repositories_bzl"]))
            or any(
                self.filepath.is_relative_to(path)
                for path
                in self.format_config.paths["protobuf"]["include"]))

    @cached_property
    def allowed_urls(self) -> bool:
        return (
            str(self.filepath)
            in self.format_config.paths["build_urls"]["include"])

    @cached_property
    def buildozer(self):
        return EnvoyBuildozer(self.buildozer_path, self.filepath)

    @cached_property
    def errors(self) -> list:
        return []

    @cached_property
    def format_config(self) -> shared.EnvoyFormatConfig:
        return shared.EnvoyFormatConfig(self.config, self.filepath)

    @cached_property
    def is_api(self) -> bool:
        return self.filepath.parts[0] == self.api_prefix

    @cached_property
    def is_api_envoy(self) -> bool:
        return (
            self.is_api
            and self.filepath.parts[1] == "envoy")

    @cached_property
    def is_build(self) -> bool:
        return (
            not self.is_starlark
            and not self.is_workspace
            and not self.is_external_build)

    @property
    def is_build_fixer_excluded(self) -> bool:
        return any(
            self.filepath.is_relative_to(path)
            for path
            in self.format_config.paths["build_fixer"]["exclude"])

    @cached_property
    def is_external_build(self) -> bool:
        return any(
            self.filepath.is_relative_to(path)
            for path
            in ("bazel/external",
                "tools/clang_tools"))

    @cached_property
    def is_mobile(self) -> bool:
        return self.filepath.parts[0] == "mobile"

    @cached_property
    def is_package(self) -> bool:
        return (
            self.is_build
            and not self.is_api
            and not self.is_build_fixer_excluded)

    @cached_property
    def is_starlark(self) -> bool:
        return self.filepath.name.endswith(".bzl")

    @cached_property
    def is_workspace(self) -> bool:
        return self.filepath.name == "WORKSPACE"

    @cached_property
    def re_contrib_package_load_block(self) -> Pattern[str]:
        return re.compile(RE_CONTRIB_PACKAGE_LOAD_BLOCK, re.DOTALL)

    @cached_property
    def re_envoy_rule(self) -> Pattern[str]:
        return re.compile(RE_ENVOY_RULE)

    @cached_property
    def re_extension_package_load_block(self) -> Pattern[str]:
        return re.compile(RE_EXTENSION_PACKAGE_LOAD_BLOCK, re.DOTALL)

    @cached_property
    def re_mobile_package_load_block(self) -> Pattern[str]:
        return re.compile(RE_MOBILE_PACKAGE_LOAD_BLOCK, re.DOTALL)

    @cached_property
    def re_old_license(self) -> Pattern[str]:
        return re.compile(RE_OLD_LICENSES, re.MULTILINE)

    @cached_property
    def re_package_load_block(self) -> Pattern[str]:
        return re.compile(RE_PACKAGE_LOAD_BLOCK, re.DOTALL)

    @cached_property
    def text(self) -> str:
        return self.filepath.read_text()

    def bad_bazel_tools_line(self, line):
        return (
            not self.allowed_bazel_tools
            and "@bazel_tools" in line
            and "python/runfiles" not in line)

    def bad_envoy_line(self, line):
        return (
            self.is_build
            and not self.is_mobile
            and "@envoy//" in line)

    def bad_protobuf_line(self, line):
        return (
            not self.allowed_protobuf_direct
            and '"protobuf"' in line)

    def bad_url_line(self, line):
        return (
            not self.allowed_urls
            and (" urls = " in line
                 or " url = " in line))

    def fix_build_line(self, line: str) -> str:
        if self.bad_bazel_tools_line(line):
            self.errors.append(
                "unexpected @bazel_tools reference, "
                "please indirect via a definition in //bazel")
        if self.bad_protobuf_line(line):
            self.errors.append(
                "unexpected direct external dependency on protobuf, use "
                "//source/common/protobuf instead.")
        if self.bad_envoy_line(line):
            self.errors.append("Superfluous '@envoy//' prefix")
            line = line.replace("@envoy//", "//")
        if self.bad_url_line(line):
            self.errors.append(
                "Only repository_locations.bzl may contains URL references")
        return line

    def handle(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        errors = '\n'.join(self.errors)
        return (
            {str(self.filepath): checker.Problems(
                errors=[f"{self.filepath}\n{errors}"])}
            if errors
            else {})

    def handle_error(
            self,
            response: subprocess.CompletedProcess) -> typing.ProblemDict:
        return {
            str(self.filepath): checker.Problems(
                errors=[f"{self.filepath}\n{self._diff(response)}"])}

    def has_failed(self, response: subprocess.CompletedProcess) -> bool:
        return bool(self._diff(response))

    def preprocess(self, text: str) -> str:
        if self.is_build:
            text = self.xform_build(text)
        if self.is_package:
            text = self.xform_package(text)
            text = self.xform_deps_api(text)
        if self.is_api_envoy:
            text = self.xform_api_package(text)
        return text

    def subprocess_args(self, *args, **kwargs) -> tuple[Sequence[str], ...]:
        if self.is_workspace:
            args = (*args, "-type=workspace")
        return super().subprocess_args(*args, **kwargs)

    def subprocess_kwargs(self, *args, **kwargs) -> Mapping:
        return {
            **self.kwargs,
            "input": self.preprocess(self.text),
            **kwargs}

    # Infer and adjust rule dependencies in BUILD files for @envoy_api proto
    # files. This is very cheap to do purely via a grep+buildozer syntax level
    # step.
    #
    # This could actually be done much more generally, for all symbols and
    # headers if we made use of Clang libtooling semantic analysis. However,
    # this requires a compilation database and full build of Envoy,
    # envoy_build_fixer.py is run under check_format, which should be fast
    # for developers.
    def xform_deps_api(self, text: str) -> str:
        return (
            self.buildozer.run(cmds, text)
            if (cmds := self.buildozer.mutation_cmds(text))
            else text)

    def xform_api_package(self, text: str):
        if "api_proto_package(" not in text:
            self.errors.append(
                "API build file does not provide api_proto_package()")
        return text

    def xform_build(self, text: str) -> str:
        return "\n".join(
            self.fix_build_line(line)
            for line
            in text.split("\n"))

    # Add an Apache 2 license, envoy_package / envoy_mobile_package import
    # and rule as needed.
    def xform_package(self, contents):
        regex_to_use = self.re_package_load_block
        package_string = 'envoy_package'
        path = str(self.filepath)

        if 'source/extensions' in path or 'library/common/extensions' in path:
            regex_to_use = self.re_package_load_block
            package_string = 'envoy_extension_package'

        if not self.is_mobile:
            if 'contrib/' in path:
                regex_to_use = self.re_contrib_package_load_block
                package_string = 'envoy_contrib_package'
        elif 'library/common/extensions' not in path:
            regex_to_use = self.re_mobile_package_load_block
            package_string = 'envoy_mobile_package'

        # Ensure we have an envoy_package / envoy_mobile_package import load
        # if this is a real Envoy package.
        # We also allow the prefix to be overridden if envoy is included
        # in a larger workspace.
        if self.re_envoy_rule.search(contents):
            new_load = (
                "new_load {}//bazel:envoy_build_system.bzl "
                f"{package_string}")
            default_prefix = ("@envoy" if self.is_mobile else "")
            contents = self.buildozer.run(
                [(new_load.format(
                    os.getenv(
                        "ENVOY_BAZEL_PREFIX",
                        default_prefix)),
                 '__pkg__')],
                contents)
            # Envoy package is inserted after the load block containing the
            # envoy_package / envoy_mobile_package import.
            package_and_parens = f"{package_string}()"
            if package_and_parens[:-1] not in contents:
                contents = regex_to_use.sub(
                    rf"\1\n{package_and_parens}\n\n",
                    contents)
                if package_and_parens not in contents:
                    raise exceptions.FixError(
                        "Unable to insert {package_and_parens}")

        # Delete old licenses.
        if self.re_old_license.search(contents):
            contents = self.re_old_license.sub('', contents)
        # Add canonical Apache 2 license.
        return f"{LICENSE_STRING}{contents}"

    def _diff(self, response: subprocess.CompletedProcess) -> str:
        if self._diff_output:
            return self._diff_output
        stdout_lines = response.stdout.splitlines()
        file_lines = self.text.splitlines()
        self._diff_output = "\n".join(
            difflib.unified_diff(
                file_lines,
                stdout_lines,
                fromfile=str(self.filepath),
                tofile=str(self.filepath)))
        return self._diff_output


@abstracts.implementer(interface.IBazelCheck)
class ABazelCheck(abstract.AFileCodeCheck, metaclass=abstracts.Abstraction):

    @classmethod
    def filter_files(
            cls,
            files: set[str],
            match: Callable,
            exclude: Callable) -> set[str]:
        """Filter files for `buildifier` checking."""
        return set(
            path
            for path
            in files
            if match(path)
            and not exclude(path))

    @classmethod
    def run_buildifier(
            cls,
            path: str,
            config: typing.YAMLConfigDict,
            buildozer_path: pathlib.Path,
            *args) -> typing.ProblemDict:
        """Run buildifier on files."""
        return EnvoyBuildifier(
            path,
            config=config,
            filepath=pathlib.Path(args[-1]),
            buildozer_path=buildozer_path).run(*args[:-1])

    @cached_property
    def buildifier_command(self) -> partial:
        """Partial with buildifier command and args."""
        return partial(
            self.run_buildifier,
            self.directory.path,
            self.config,
            self.buildozer_path,
            self.buildifier_path,
            "-mode=fix",
            "-lint=fix")

    @cached_property
    def buildifier_path(self) -> pathlib.Path:
        """Buildifier command, should be available in the running system."""
        return self.command_path("buildifier")

    @cached_property
    def buildozer_path(self) -> pathlib.Path:
        """Buildozer command, should be available in the running system."""
        return self.command_path("buildozer")

    @async_property
    async def checker_files(self) -> set[str]:
        return self.filter_files(
            await self.directory.files,
            self.re_path_match.match,
            self.exclude)

    @async_property(cache=True)
    async def problem_files(self) -> typing.ProblemDict:
        """Discovered bazel errors."""
        if not await self.files:
            return {}
        errors: typing.ProblemDict = dict()
        jobs = tasks.concurrent(
            self.execute(
                self.buildifier_command,
                file)
            for file
            in await self.files)
        async for result in jobs:
            errors.update(result)
        return errors

    @cached_property
    def re_path_match(self) -> Pattern[str]:
        """Regex to match files to check."""
        return re.compile("|".join(RE_BAZEL_MATCH))

    def exclude(self, path: str) -> bool:
        return path.startswith(
            tuple(self.config["paths"]["excluded"]))
