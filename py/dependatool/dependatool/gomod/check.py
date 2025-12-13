
import abstracts

from dependatool import ADependatoolCheck
from .abstract import ADependatoolGomodCheck


@abstracts.implementer(ADependatoolCheck)
class DependatoolGomodCheck(ADependatoolGomodCheck):
    pass
