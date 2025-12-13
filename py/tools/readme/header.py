
import argparse
import pathlib
import sys
from functools import cached_property

import jinja2

from aio.run import runner


class ReadmeHeaderRunner(runner.Runner):

    @cached_property
    def template(self):
        return jinja2.Template(pathlib.Path(self.args.template).read_text())

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("template")

    async def run(self):
        print(self.template.render())


def main(*args):
    return ReadmeHeaderRunner(*args)()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
