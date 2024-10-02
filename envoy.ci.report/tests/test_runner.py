
from envoy.ci import report


def test_runner_constructor():
    runner = report.ReportRunner()
    assert isinstance(runner, report.interface.IReportRunner)
    assert isinstance(runner, report.abstract.AReportRunner)


def test_runner_runs_class():
    runner = report.ReportRunner()
    assert (
        runner.runs_class
        == report.ci.CIRuns)
    assert "runs_class" not in runner.__dict__


def test_runner_runs_registered_filters():
    runner = report.ReportRunner()
    assert (
        runner.registered_filters
        == dict(
            status=report.StatusFilter,
            created=report.CreationTimeFilter))
    assert "registered_filters" in runner.__dict__


def test_runner_runs_registered_formats():
    runner = report.ReportRunner()
    assert (
        runner.registered_formats
        == dict(
            json=report.JSONFormat,
            markdown=report.MarkdownFormat))
    assert "registered_formats" in runner.__dict__
