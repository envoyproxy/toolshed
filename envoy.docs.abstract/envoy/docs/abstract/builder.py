
import abstracts


class ADocsBuilder(metaclass=abstracts.Abstraction):

    def __init__(self, out, api_files) -> None:
        self.out = out
        self._api_files = api_files
