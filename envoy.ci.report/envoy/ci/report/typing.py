
from typing import TypedDict


class CIWorkflowDict(TypedDict):
    name: str
    status: str
    event: str
    conclusion: str


class CICommitHeadDict(TypedDict):
    message: str
    target_branch: str


class CIRequestDict(TypedDict):
    event: str
    started: float
    workflows: list[dict[str, CIWorkflowDict]]


class CIRunsCommitDict(TypedDict):
    head: CICommitHeadDict
    requests: dict[int, CIRequestDict]


class CIRequestWorkflowDict(TypedDict):
    checks: dict
    request: dict


CIRunsDict = dict[str, CIRunsCommitDict]
CIRequestWorkflowsDict = dict[int, list[CIRequestWorkflowDict]]
CIRequestEventDict = dict[str, CIRequestWorkflowsDict]
CIRequestEnvsDict = dict[str, CIRequestEventDict]
