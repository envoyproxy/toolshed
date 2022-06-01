
import argparse
import importlib
import pathlib
from typing import Callable, Dict, Iterable, Optional

import jinja2


class JinjaEnvironment:

    @classmethod
    @property
    def parser_create(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument("outpath")
        parser.add_argument("-t", "--template", nargs="+")
        parser.add_argument("-f", "--filter", action="append")
        return parser

    @classmethod
    @property
    def parser_load(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument("template_py")
        parser.add_argument("-f", "--filter", action="append")
        return parser

    @classmethod
    def create(cls, *args: str) -> None:
        parsed = cls.parser_create.parse_args(args)  # type:ignore
        env = cls._env(
            jinja2.FileSystemLoader(
                list(set(
                    pathlib.Path(t).parent
                    for t
                    in (parsed.template or [])))),
            parsed.filter)
        env.compile_templates(parsed.outpath)

    @classmethod
    def load(cls, *args: str, **kwargs) -> jinja2.Environment:
        parsed = cls.parser_load.parse_args(args)  # type:ignore
        return cls._env(
            jinja2.ModuleLoader(parsed.template_py),
            parsed.filter,
            **kwargs)

    @classmethod
    def _env(
            cls,
            loader: jinja2.BaseLoader,
            filters: Optional[Iterable[str]],
            **kwargs) -> jinja2.Environment:
        env = jinja2.Environment(loader=loader, **kwargs)
        env.filters.update(cls._filters(filters))
        return env

    @classmethod
    def _filter(cls, filter_path: str) -> Callable:
        parts = filter_path.split(".")
        return getattr(
            importlib.import_module(".".join(parts[:-1])),
            parts[-1])

    @classmethod
    def _filters(cls, filters: Optional[Iterable[str]]) -> Dict[str, Callable]:
        return {
            (parts := f.split(":"))[0]: cls._filter(parts[1])
            for f
            in filters or []}
