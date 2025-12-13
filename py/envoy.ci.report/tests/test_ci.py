
from envoy.ci import report


def test_ciruns_constructor():
    runs = report.CIRuns("REPO")
    assert isinstance(runs, report.interface.ICIRuns)
    assert isinstance(runs, report.abstract.ACIRuns)
