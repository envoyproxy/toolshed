
from typing import Dict, List, Optional, Tuple, TypedDict

from aio.run import checker


ProblemDict = Dict[str, checker.interface.IProblems]

YamllintProblemTuple = Tuple[str, checker.interface.IProblems]

YapfProblemTuple = Tuple[str, checker.interface.IProblems]
YapfResultTuple = Tuple[str, str, bool]
YapfCheckResultTuple = Tuple[str, YapfResultTuple]

GofmtProblemTuple = Tuple[str, checker.interface.IProblems]


class BaseExtensionMetadataDict(TypedDict):
    categories: List[str]
    security_posture: str
    status: str
    status_upstream: str


class ExtensionMetadataDict(BaseExtensionMetadataDict, total=False):
    undocumented: bool
    type_urls: List[str]


ExtensionsMetadataDict = Dict[str, ExtensionMetadataDict]
ExtensionsSchemaCategoriesList = List[str]
ExtensionsSchemaBuiltinList = List[str]
ExtensionsSchemaSecurityPosturesList = List[str]
ExtensionsSchemaStatusValuesList = List[str]


class ExtensionSecurityPostureMetadataDict(TypedDict):
    name: str
    description: str


class ExtensionStatusMetadataDict(TypedDict):
    name: str
    description: Optional[str]


class ExtensionsSchemaDict(TypedDict):
    builtin: ExtensionsSchemaBuiltinList
    security_postures: List[ExtensionSecurityPostureMetadataDict]
    categories: ExtensionsSchemaCategoriesList
    status_values: List[ExtensionStatusMetadataDict]


ConfiguredExtensionsDict = Dict[str, str]
