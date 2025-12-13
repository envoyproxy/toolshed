
from typing import Any


class CollectionQueryError(Exception):
    pass


class TypeCastingError(TypeError):

    def __init__(self, *args,  value: Any = None) -> None:
        self.value = value
        super().__init__(*args)


class BatchedJobsError(Exception):
    pass
