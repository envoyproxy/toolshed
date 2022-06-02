
import argparse
import pathlib
import pickle
from typing import Any

from envoy.base import utils


class DataEnvironment:

    @classmethod
    @property
    def parser_create(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument("data")
        parser.add_argument("outpath")
        parser.add_argument("-f", "--format", default="json")
        return parser

    @classmethod
    @property
    def parser_load(cls) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()
        parser.add_argument("pickle")
        return parser

    @classmethod
    def create(cls, *args: str) -> None:
        parsed = cls.parser_create.parse_args(args)  # type:ignore
        with open(parsed.outpath, "wb") as f:
            pickle.dump(
                cls._data(parsed.data, parsed.format),
                f,
                pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, *args: str) -> Any:
        parsed = cls.parser_load.parse_args(args)  # type:ignore
        with open(parsed.pickle, 'rb') as f:
            return pickle.load(f)

    @classmethod
    def _data(cls, data: pathlib.Path | str, format: str):
        if format == "yaml":
            return utils.from_yaml(data)
        return utils.from_json(data)
