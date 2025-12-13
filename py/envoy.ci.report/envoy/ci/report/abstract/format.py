
import json
import textwrap
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
        for commit, info in data.items():
            self._handle_commit(commit, info)

    def _handle_commit(self, commit: str, info: dict) -> None:
        target_branch = info["head"]["target_branch"]
        commit_url = f"https://github.com/envoyproxy/envoy/commit/{commit}"
        print(f"### [{target_branch}@{commit[:7]}]({commit_url})")
        self._handle_commit_message(info['head']['message'])
        for request_id, request in info["requests"].items():
            self._handle_event(request_id, request)

    def _handle_commit_message(self, message):
        lines = message.splitlines()
        if len(lines) == 1:
            print(message)
            return
        summary = lines[0]
        details = textwrap.indent(
            "\n".join(lines[1:]),
            "  ",
            lambda line: True)
        print("<details>")
        print(f"  <summary>{summary}</summary>")
        print("  <blockquote>")
        print(details)
        print("  </blockquote>")
        print("</details>")
        print()

    def _handle_event(self, request_id, request) -> None:
        event_type = request["event"]
        request_started = datetime.utcfromtimestamp(
            int(request["started"])).isoformat()
        request_url = (
            "https://github.com/envoyproxy/envoy/"
            f"actions/runs/{request_id}")
        print(f"#### [{event_type}@{request_started}]({request_url}):")
        for workflow_id, workflow in request["workflows"].items():
            workflow_url = (
                "https://github.com/envoyproxy/envoy/"
                f"actions/runs/{workflow_id}")
            print(
                f"- [{workflow['name']} "
                f"({workflow['conclusion']})]({workflow_url})")
        print()
        print("----")
