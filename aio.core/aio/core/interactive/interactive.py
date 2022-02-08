
import contextlib

import abstracts

from aio.core import interactive


@abstracts.implementer(interactive.APrompt)
class Prompt:
    pass


@abstracts.implementer(interactive.AInteractive)
class Interactive:

    @property
    def prompt_class(self):
        return Prompt


@contextlib.asynccontextmanager
async def interactive(*args, **kwargs):
    interaction = Interactive(*args, **kwargs)
    await interaction.start()
    yield interaction
