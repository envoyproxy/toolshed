
from typing import Dict, List, Tuple, TypedDict


ProblemDict = Dict[str, List[str]]

YapfProblemTuple = Tuple[str, List[str]]
YapfResultTuple = Tuple[str, str, bool]
YapfCheckResultTuple = Tuple[str, YapfResultTuple]


class BaseExtensionMetadataDict(TypedDict):
    categories: List[str]
    security_posture: List[str]
    status: List[str]


class ExtensionMetadataDict(BaseExtensionMetadataDict, total=False):
    undocumented: bool


ExtensionsMetadataDict = Dict[str, ExtensionMetadataDict]
ExtensionsSchemaCategoriesList = List[str]
ExtensionsSchemaBuiltinList = List[str]
ExtensionsSchemaSecurityPosturesList = List[str]
ExtensionsSchemaStatusValuesList = List[str]


class ExtensionSecurityPostureMetadataDict(TypedDict):
    name: str
    description: str


class ExtensionsSchemaDict(TypedDict):
    builtin: ExtensionsSchemaBuiltinList
    security_postures: List[ExtensionSecurityPostureMetadataDict]
    categories: ExtensionsSchemaCategoriesList
    status_values: ExtensionsSchemaStatusValuesList


ConfiguredExtensionsDict = Dict[str, str]
