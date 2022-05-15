
from typing import Optional

import abstracts


class IRSTCheck(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __call__(self, text: str) -> Optional[str]:
        raise NotImplementedError
