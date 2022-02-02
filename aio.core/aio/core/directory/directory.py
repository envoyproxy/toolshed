
import abstracts

from aio.core import directory


@abstracts.implementer(directory.ADirectory)
class Directory:
    pass


@abstracts.implementer(directory.AGitDirectory)
class GitDirectory:
    pass
