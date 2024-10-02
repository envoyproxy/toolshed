
import json
from datetime import datetime

import abstracts

from envoy.ci.report import interface


class AFormat(metaclass=abstracts.Abstraction):

    def __call__(self, data: dict) -> None:
        self.out(data)

    @abstracts.interfacemethod
    def out(self, data: dict) -> None:
        raise NotImplementedError


@abstracts.implementer(interface.IFormat)
class AJSONFormat(AFormat):

    def out(self, data: dict) -> None:
        print(json.dumps(data))


@abstracts.implementer(interface.IFormat)
class AMarkdownFormat(AFormat):

    def out(self, data: dict) -> None:
        for commit, events in data.items():
            self._handle_commit(commit, events)

    def _handle_commit(self, commit: str, events: list[dict]) -> None:
        outcome = (
            "failed"
            if any(event["workflow"]["conclusion"] == "failure"
                   for event
                   in events)
            else "succeeded")
        target_branch = events[0]["request"]["target-branch"]
        commit_url = f"https://github.com/envoyproxy/envoy/commit/{commit}"
        print(f"[{target_branch}@{commit[:7]}]({commit_url}): {outcome}")
        for event in events:
            self._handle_event(event)

    def _handle_event(self, event: dict) -> None:
        event_type = event["event"]
        request_started = datetime.utcfromtimestamp(
            int(event["request"]["started"])).isoformat()
        workflow_name = event["workflow"]["name"]
        conclusion = event["workflow"]["conclusion"]
        workflow_id = event["workflow_id"]
        request_id = event["request_id"]
        workflow_url = (
            "https://github.com/envoyproxy/envoy/"
            f"actions/runs/{workflow_id}")
        request_url = (
            "https://github.com/envoyproxy/envoy/"
            f"actions/runs/{request_id}")
        print(
            f" -> [[{event_type}@{request_started}]({request_url})]: "
            f"[{workflow_name} ({conclusion})]({workflow_url})")
