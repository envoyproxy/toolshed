
from dataclasses import dataclass
from typing import ClassVar, Type

from pants.backend.python.target_types import (
    PexEntryPointField,
    ResolvedPexEntryPoint, ResolvePexEntryPointRequest)
from pants.backend.python.util_rules.pex import (
    VenvPex, VenvPexProcess)
from pants.backend.python.util_rules.pex_from_targets import (
    PexFromTargetsRequest)
from pants.backend.python.util_rules.python_sources import (
    PythonSourceFiles,
    PythonSourceFilesRequest)
from pants.engine.addresses import UnparsedAddressInputs
from pants.engine.internals.selectors import MultiGet
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, Get, rule
from pants.engine.target import (
    COMMON_TARGET_FIELDS, FieldSet, SpecialCasedDependencies,
    StringField, Target, Targets, TransitiveTargets, TransitiveTargetsRequest)
from pants.engine.unions import union, UnionRule


class ReadmeSnippetTextField(SpecialCasedDependencies):
    alias = "text"
    help = "Generators for README text."


class ReadmeSnippetArtefactsField(SpecialCasedDependencies):
    alias = "artefacts"
    help = "Build artefacts to use when readmeing packages."


class ReadmeSnippetTemplateTagField(StringField):
    alias = "template_tag"
    help = "Template tag."
    default = "body"


@dataclass(frozen=True)
class ReadmeSnippetFieldSet(FieldSet):
    required_fields = (ReadmeSnippetTextField, )
    text: ReadmeSnippetTextField
    artefacts: ReadmeSnippetArtefactsField
    template_tag: ReadmeSnippetTemplateTagField


@union
@dataclass(frozen=True)
class ReadmeSnippetRequest:
    fieldset: ReadmeSnippetFieldSet


class ReadmeSnippetTarget(Target):
    alias = "readme_snippet"
    help = "Register a README snippet producer"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        ReadmeSnippetTemplateTagField,
        ReadmeSnippetTextField,
        ReadmeSnippetArtefactsField)
    readme_request_type: ClassVar[
        Type[ReadmeSnippetRequest]] = ReadmeSnippetRequest
    readmeee_fieldset_type: ClassVar[
        Type[ReadmeSnippetFieldSet]] = ReadmeSnippetFieldSet


@dataclass(frozen=True)
class ReadmeSnippet:
    text: StringField


@rule
async def readme_snippet(
        request: ReadmeSnippetRequest) -> ReadmeSnippet:
    artefacts, text_processors = await MultiGet(
        Get(
            Targets,
            UnparsedAddressInputs,
            request.fieldset.artefacts.to_unparsed_address_inputs()),
        Get(Targets,
            UnparsedAddressInputs,
            request.fieldset.text.to_unparsed_address_inputs()))

    # Build the text processor and get the entry point
    text_processor = text_processors[0]
    resolved_entry_point, transitive_targets = await MultiGet(
        Get(ResolvedPexEntryPoint,
            ResolvePexEntryPointRequest(
                text_processor[PexEntryPointField])),
        Get(TransitiveTargets,
            TransitiveTargetsRequest(
                [text_processor.address])))

    filename_parts = [
        "readme",
        request.fieldset.template_tag.value,
        "snippet.pex"]
    parent = request.fieldset.address.spec.split(':')[0].strip('/')
    if parent:
        filename_parts = [parent] + filename_parts
    output_filename = "_".join(filename_parts)

    input_digest = None
    argv = ()
    if artefacts:
        transitive_targets = await Get(
            TransitiveTargets,
            TransitiveTargetsRequest(
                [artefact.address
                 for artefact
                 in artefacts]))
        sources = await Get(
            PythonSourceFiles,
            PythonSourceFilesRequest(
                transitive_targets.closure,
                include_files=True))
        input_digest = sources.source_files.snapshot.digest
        # TODO: switch order
        argv = (sources.source_files.files[-1], *sources.source_roots[:-1])

    # get the pex binary
    pex = await Get(
        VenvPex,
        PexFromTargetsRequest(
            addresses=(text_processor.address, ),
            internal_only=True,
            include_source_files=True,
            main=resolved_entry_point.val,
            output_filename=output_filename))

    # TODO: merge pex.digest ?

    # run the pex with artefacts
    process = await Get(
        ProcessResult,
        VenvPexProcess(
            pex,
            description="Generating snippet",
            argv=argv,
            input_digest=input_digest))
    return ReadmeSnippet(text=process.stdout)


def target_types():
    return [ReadmeSnippetTarget]


def rules():
    return (
        *collect_rules(),
        UnionRule(ReadmeSnippetRequest, ReadmeSnippetRequest))
