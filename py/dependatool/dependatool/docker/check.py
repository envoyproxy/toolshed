
import abstracts

from dependatool import ADependatoolCheck
from .abstract import ADependatoolDockerCheck


@abstracts.implementer(ADependatoolCheck)
class DependatoolDockerCheck(ADependatoolDockerCheck):
    pass
