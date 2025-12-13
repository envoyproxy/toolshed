
from unittest.mock import MagicMock, PropertyMock

import pytest

from envoy.ci import report


class DummyWorkflowFilter(report.abstract.AWorkflowFilter):

    @property
    def filter_string(self) -> str:
        return str(self.args.filter_string_called())


def test_filter_constructor():
    args = MagicMock()
    with pytest.raises(TypeError):
        report.abstract.AWorkflowFilter(args)
    DummyWorkflowFilter(args)


def test_filter_filter_string():
    args = MagicMock()
    filter = DummyWorkflowFilter(args)
    assert (
        str(filter)
        == str(args.filter_string_called.return_value))


def test_statusfilter_constructor():
    assert isinstance(
        report.abstract.AStatusFilter(MagicMock()),
        report.interface.IWorkflowFilter)


@pytest.mark.parametrize("status", ["all", "foo", "bar"])
def test_statusfilter_filter_string(status):
    args = MagicMock()
    args.status = status
    filter = report.abstract.AStatusFilter(args)
    assert (
        filter.filter_string
        == (""
            if status == "all"
            else status))
    assert "filter_string" not in filter.__dict__


def test_creationtimefilter_constructor():
    assert isinstance(
        report.abstract.ACreationTimeFilter(MagicMock()),
        report.interface.IWorkflowFilter)


@pytest.mark.parametrize("start", ["START", None])
@pytest.mark.parametrize("end", ["END", None])
def test_creationtimefilter_filter_string(patches, start, end):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    expected = ""
    if start and end:
        expected = f"{start}..{end}"
    elif start:
        expected = f">{start}"
    patched = patches(
        ("ACreationTimeFilter.time_end_string",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.time_start_string",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_end, m_start):
        m_end.return_value = end
        m_start.return_value = start
        assert (
            filter.filter_string
            == expected)

    assert "filter_string" not in filter.__dict__


def test_creationtimefilter_now(patches):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        "datetime",
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_dt, ):
        assert (
            filter.now
            == m_dt.utcnow.return_value)

    assert "now" in filter.__dict__
    assert (
        m_dt.utcnow.call_args
        == [(), {}])


def test_creationtimefilter_start_day(patches):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        ("ACreationTimeFilter.now",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_now, ):
        assert (
            filter.start_day
            == m_now.return_value.replace.return_value)

    assert "start_day" in filter.__dict__
    assert (
        m_now.return_value.replace.call_args
        == [(), dict(hour=0, minute=0, second=0, microsecond=0)])


def test_creationtimefilter_start_hour(patches):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        ("ACreationTimeFilter.now",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_now, ):
        assert (
            filter.start_hour
            == m_now.return_value.replace.return_value)

    assert "start_hour" in filter.__dict__
    assert (
        m_now.return_value.replace.call_args
        == [(), dict(minute=0, second=0, microsecond=0)])


def test_creationtimefilter_start_week(patches):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        "timedelta",
        ("ACreationTimeFilter.now",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_delta, m_now):
        assert (
            filter.start_week
            == m_now.return_value.__sub__.return_value.replace.return_value)

    assert "start_week" in filter.__dict__
    assert (
        m_now.return_value.__sub__.call_args
        == [(m_delta.return_value, ), {}])
    assert (
        m_delta.call_args
        == [(), dict(days=m_now.return_value.weekday.return_value)])
    assert (
        m_now.return_value.weekday.call_args
        == [(), {}])
    assert (
        m_now.return_value.__sub__.return_value.replace.call_args
        == [(), dict(hour=0, minute=0, second=0, microsecond=0)])


@pytest.mark.parametrize("previous", ["day", "week", "hour", "banana", None])
def test_creationtimefilter_time_end(patches, previous):
    args = MagicMock()
    args.previous = previous
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        ("ACreationTimeFilter.start_day",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.start_hour",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.start_week",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_day, m_hour, m_week):
        if previous == "day":
            expected = m_day.return_value
        elif previous == "hour":
            expected = m_hour.return_value
        elif previous == "week":
            expected = m_week.return_value
        else:
            expected = None
        assert (
            filter.time_end
            == expected)

    assert "time_end" in filter.__dict__


@pytest.mark.parametrize("end", [True, False])
def test_creationtimefilter_time_end_string(patches, end):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        ("ACreationTimeFilter.time_end",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")
    time_end = (
        MagicMock()
        if end
        else None)

    with patched as (m_end, ):
        m_end.return_value = time_end
        assert (
            filter.time_end_string
            == (time_end.strftime.return_value
                if end
                else ""))

    assert "time_end_string" not in filter.__dict__
    if not end:
        return
    assert (
        time_end.strftime.call_args
        == [("%Y-%m-%dT%H:%M:%SZ", ), {}])


@pytest.mark.parametrize("current", ["day", "week", "hour", "banana", None])
@pytest.mark.parametrize("previous", ["day", "week", "hour", "banana", None])
def test_creationtimefilter_time_start(patches, current, previous):
    args = MagicMock()
    args.current = current
    args.previous = previous
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        "timedelta",
        ("ACreationTimeFilter.now",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.start_day",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.start_hour",
         dict(new_callable=PropertyMock)),
        ("ACreationTimeFilter.start_week",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")

    with patched as (m_delta, m_now, m_day, m_hour, m_week):
        if current == "day":
            expected = m_day.return_value
        elif current == "hour":
            expected = m_hour.return_value
        elif current == "week":
            expected = m_week.return_value
        elif previous == "day":
            expected = m_day.return_value.__sub__.return_value
        elif previous == "hour":
            expected = m_hour.return_value.__sub__.return_value
        elif previous == "week":
            expected = m_week.return_value.__sub__.return_value
        else:
            expected = m_now.return_value.__sub__.return_value
        assert (
            filter.time_start
            == expected)

    assert "time_start" in filter.__dict__
    if current in ["day", "week", "hour"]:
        assert not m_delta.called
    elif previous == "day":
        assert (
            m_delta.call_args
            == [(), dict(days=1)])
    elif previous == "hour":
        assert (
            m_delta.call_args
            == [(), dict(hours=1)])
    elif previous == "week":
        assert (
            m_delta.call_args
            == [(), dict(weeks=1)])
    else:
        assert (
            m_delta.call_args
            == [(), dict(hours=(24 * 7))])


@pytest.mark.parametrize("start", [True, False])
def test_creationtimefilter_time_start_string(patches, start):
    args = MagicMock()
    filter = report.abstract.ACreationTimeFilter(args)
    patched = patches(
        ("ACreationTimeFilter.time_start",
         dict(new_callable=PropertyMock)),
        prefix="envoy.ci.report.abstract.filters")
    time_start = (
        MagicMock()
        if start
        else None)

    with patched as (m_start, ):
        m_start.return_value = time_start
        assert (
            filter.time_start_string
            == (time_start.strftime.return_value
                if start
                else ""))

    assert "time_start_string" not in filter.__dict__
    if not start:
        return
    assert (
        time_start.strftime.call_args
        == [("%Y-%m-%dT%H:%M:%SZ", ), {}])
