
import abstracts

from dependatool import ADependatoolCheck
from .abstract import ADependatoolNPMCheck


@abstracts.implementer(ADependatoolCheck)
class DependatoolNPMCheck(ADependatoolNPMCheck):
    pass
