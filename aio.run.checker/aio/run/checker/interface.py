
from typing import List

import abstracts


class IProblems(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def errors(self) -> List[str]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def warnings(self) -> List[str]:
        raise NotImplementedError
