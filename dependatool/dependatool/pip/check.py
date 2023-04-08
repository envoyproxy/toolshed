
import abstracts

from dependatool import ADependatoolCheck
from .abstract import ADependatoolPipCheck


@abstracts.implementer(ADependatoolCheck)
class DependatoolPipCheck(ADependatoolPipCheck):
    pass
