
import argparse
from datetime import datetime, timedelta
from functools import cached_property

import abstracts

from envoy.ci.report import interface


class AWorkflowFilter(metaclass=abstracts.Abstraction):

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    def __str__(self) -> str:
        return self.filter_string

    @property
    @abstracts.interfacemethod
    def filter_string(self) -> str:
        raise NotImplementedError


@abstracts.implementer(interface.IWorkflowFilter)
class AStatusFilter(AWorkflowFilter):

    @property
    def filter_string(self) -> str:
        if self.args.status == "all":
            return ""
        return self.args.status


@abstracts.implementer(interface.IWorkflowFilter)
class ACreationTimeFilter(AWorkflowFilter):

    @property
    def filter_string(self) -> str:
        if self.time_start_string and self.time_end_string:
            return f"{self.time_start_string}..{self.time_end_string}"
        elif self.time_start_string:
            return f">{self.time_start_string}"
        return ""

    @cached_property
    def now(self) -> datetime:
        return datetime.utcnow()

    @cached_property
    def start_day(self) -> datetime:
        return self.now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0)

    @cached_property
    def start_hour(self) -> datetime:
        return self.now.replace(
            minute=0,
            second=0,
            microsecond=0)

    @cached_property
    def start_week(self) -> datetime:
        return (
            self.now
            - timedelta(days=self.now.weekday())).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0)

    @cached_property
    def time_end(self) -> datetime | None:
        match self.args.previous:
            case "day":
                return self.start_day
            case "week":
                return self.start_week
            case "hour":
                return self.start_hour
            case _:
                return None

    @property
    def time_end_string(self) -> str:
        return (
            self.time_end.strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.time_end
            else "")

    @cached_property
    def time_start(self) -> datetime:
        match (self.args.current, self.args.previous):
            case ("day", _):
                return self.start_day
            case ("week", _):
                return self.start_week
            case ("hour", _):
                return self.start_hour
            case (_, "day"):
                return self.start_day - timedelta(days=1)
            case (_, "week"):
                return self.start_week - timedelta(weeks=1)
            case (_, "hour"):
                return self.start_hour - timedelta(hours=1)
            case _:
                # default max is 1 week
                # TODO: allow start/end times to be set directly
                return self.now - timedelta(hours=(24 * 7))

    @property
    def time_start_string(self) -> str:
        return (
            self.time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            if self.time_start
            else "")
