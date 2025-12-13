
import abstracts

from envoy.ci import report


@abstracts.implementer(report.interface.ICIRuns)
class CIRuns(report.abstract.ACIRuns):
    pass
