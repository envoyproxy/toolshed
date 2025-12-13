
import abstracts

from aio.api import github


class ICIRuns(metaclass=abstracts.Interface):

    def __init__(
            self,
            repo: github.interface.IGithubRepo,
            filters: dict[str, str] | None = None,
            ignored: dict | None = None,
            sort_ascending: bool | None = None) -> None:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    async def as_dict(self) -> dict:
        raise NotImplementedError


class IFormat(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def out(self, data: dict) -> None:
        raise NotImplementedError


class IReportRunner(metaclass=abstracts.Interface):

    @property
    @abstracts.interfacemethod
    def registered_filters(self) -> dict:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def registered_formats(self) -> dict:
        raise NotImplementedError


class IWorkflowFilter(metaclass=abstracts.Interface):

    def __init__(self, args) -> None:
        raise NotImplementedError

    @property
    @abstracts.interfacemethod
    def filter_string(self) -> str:
        raise NotImplementedError
