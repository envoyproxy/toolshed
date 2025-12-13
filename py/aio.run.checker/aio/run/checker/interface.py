
import abstracts


class IProblems(metaclass=abstracts.Interface):

    @property  # type:ignore
    @abstracts.interfacemethod
    def errors(self) -> list[str]:
        raise NotImplementedError

    @property  # type:ignore
    @abstracts.interfacemethod
    def warnings(self) -> list[str]:
        raise NotImplementedError
