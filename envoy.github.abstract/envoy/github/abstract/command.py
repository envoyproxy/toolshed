
import argparse
import pathlib
from functools import cached_property
from typing import Dict, Optional, List, Tuple

import abstracts

from envoy.abstract import command

from .release import AGithubRelease
from .runner import AGithubReleaseRunner
from .manager import AGithubReleaseManager


class AGithubReleaseCommand(
        command.AAsyncCommand,
        metaclass=abstracts.Abstraction):

    @cached_property
    def artefacts(self) -> Tuple[pathlib.Path, ...]:
        return tuple(
            pathlib.Path(asset)
            for asset
            in getattr(self.args, "assets", []))

    @cached_property
    def manager(self) -> AGithubReleaseManager:
        return self.runner.release_manager

    @cached_property
    def parser(self) -> argparse.ArgumentParser:
        return super().parser

    @cached_property
    def release(self) -> AGithubRelease:
        return self.manager[self.version]

    @property
    def runner(self) -> AGithubReleaseRunner:
        return self.context

    @property
    def version(self) -> str:
        return self.args.version

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("version", help="Github release version")

    def format_response(
            self,
            release: Optional[Dict] = None,
            assets: Optional[List[Dict]] = None,
            errors: Optional[List[Dict]] = None) -> Optional[int]:
        for k, v in (release or {}).items():
            if isinstance(v, dict):
                print(k)
                for _k, _v in v.items():
                    _k = f"{k}.{_k}"
                    print('{0:<30} {1}'.format(_k, _v or ""))
                continue
            if isinstance(v, list):
                continue
            print('{0:<30} {1}'.format(k, v or ""))
        for i, result in enumerate(assets or []):
            k = "assets" if i == 0 else ""
            print('{0:<30} {1:<30} {2}'.format(
                k, result["name"], result["url"]))
        return 1 if errors else 0
