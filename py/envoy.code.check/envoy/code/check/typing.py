
from typing import TypedDict

from aio.run import checker


ProblemDict = dict[str, checker.interface.IProblems]

YamllintProblemTuple = tuple[str, checker.interface.IProblems]

YapfProblemTuple = tuple[str, checker.interface.IProblems]
YapfResultTuple = tuple[str, str, bool]
YapfCheckResultTuple = tuple[str, YapfResultTuple]

GofmtProblemTuple = tuple[str, checker.interface.IProblems]


class BaseExtensionMetadataDict(TypedDict):
    categories: list[str]
    security_posture: str
    status: str


class ExtensionMetadataDict(BaseExtensionMetadataDict, total=False):
    undocumented: bool
    type_urls: list[str]
    status_upstream: str


ExtensionsMetadataDict = dict[str, ExtensionMetadataDict]
ExtensionsSchemaCategoriesList = list[str]
ExtensionsSchemaBuiltinList = list[str]
ExtensionsSchemaSecurityPosturesList = list[str]
ExtensionsSchemaStatusValuesList = list[str]


class ExtensionSecurityPostureMetadataDict(TypedDict):
    name: str
    description: str


class ExtensionStatusMetadataDict(TypedDict):
    name: str
    description: str | None


class ExtensionsSchemaDict(TypedDict):
    builtin: ExtensionsSchemaBuiltinList
    security_postures: list[ExtensionSecurityPostureMetadataDict]
    categories: ExtensionsSchemaCategoriesList
    status_values: list[ExtensionStatusMetadataDict]


ConfiguredExtensionsDict = dict[str, str]
YAMLConfigDict = dict[str, str | list | dict[str, 'YAMLConfigDict']]
