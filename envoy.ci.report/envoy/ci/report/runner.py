
from functools import cached_property
from typing import Type

import abstracts

from envoy.ci.report import abstract, ci, interface


class JSONFormat(abstract.AJSONFormat):
    pass


class MarkdownFormat(abstract.AMarkdownFormat):
    pass


class StatusFilter(abstract.AStatusFilter):
    pass


class CreationTimeFilter(abstract.ACreationTimeFilter):
    pass


@abstracts.implementer(interface.IReportRunner)
class ReportRunner(abstract.AReportRunner):
    """This runner interacts with the Github action API to parse information
    about Envoy's CI."""

    @property
    def runs_class(self) -> Type[interface.ICIRuns]:
        return ci.CIRuns

    @cached_property
    def registered_filters(self):
        return dict(
            status=StatusFilter,
            created=CreationTimeFilter)

    @cached_property
    def registered_formats(self):
        return dict(
            json=JSONFormat,
            markdown=MarkdownFormat)
