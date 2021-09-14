
import logging
from dataclasses import dataclass
from typing import ClassVar, Iterable, List, Tuple, Type, cast

from pants.engine.process import Process, ProcessResult
from pants.build_graph.address import Address
from pants.backend.python.target_types import PythonDistributionDependencies, PexEntryPointField, ResolvedPexEntryPoint, ResolvePexEntryPointRequest
from pants.engine.console import Console
from pants.engine.target import COMMON_TARGET_FIELDS, FieldSet, SpecialCasedDependencies, StringField, Target, Targets, TransitiveTargets, TransitiveTargetsRequest
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, collect_rules, goal_rule, rule
from pants.engine.unions import UnionMembership, union
from pants.engine.addresses import UnparsedAddressInputs
from pants.engine.process import FallibleProcessResult
from pants.core.goals.package import BuiltPackage, PackageFieldSet
from pants.engine.internals.selectors import MultiGet
from pants.util.meta import frozen_after_init
from pants.util.ordered_set import FrozenOrderedSet
from pants.engine.unions import UnionRule
from pants.backend.python.util_rules.pex import Pex, PexRequest, PexRequirements, VenvPex, VenvPexProcess
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest

from pytooling_distribution import PytoolingDistribution


logger = logging.getLogger(__name__)


class VerifySubsystem(GoalSubsystem):
    name = "verify"
    help = "Verify packages."


class Verify(Goal):
    subsystem_cls = VerifySubsystem


def _can_package(target: Target, union_membership: UnionMembership):
    package_request_types = cast(Iterable[Type[PackageFieldSet]], union_membership[PackageFieldSet])

    for fieldset in package_request_types:
        if fieldset.is_applicable(target):
            return fieldset

    return False


class VerifyTargetField(SpecialCasedDependencies):
    alias = "verify_targets"
    help = "Verifications."


@dataclass(frozen=True)
class VerifyTargetFieldSet(FieldSet):
    required_fields = (VerifyTargetField,)


@union
@dataclass(frozen=True)
class VerifyRequest:
    package: BuiltPackage
    fieldset: VerifyTargetFieldSet
    target: "VerifyTarget"


class VerificationVerifier(SpecialCasedDependencies):
    alias = "verifier"
    help = "The name of a verifier."


class InterpolatingSpecialCasedDependencies(SpecialCasedDependencies):
    """Subclass this for fields that act similarly to the `dependencies` field, but are handled
    """

    def to_unparsed_address_inputs(self, **values) -> UnparsedAddressInputs:
        return UnparsedAddressInputs(tuple(v.format(**values) for v in self.value or ()), owning_address=self.address)


class VerificationBuildArtefacts(InterpolatingSpecialCasedDependencies):
    alias = "build_artefacts"
    help = "Build artefacts to use when verifying packages."


class VerifyTarget(Target):
    core_fields = (*COMMON_TARGET_FIELDS,)
    verify_request_type: ClassVar[Type[VerifyRequest]]
    verifyee_fieldset_type: ClassVar[Type[VerifyTargetFieldSet]] = VerifyTargetFieldSet


@dataclass(frozen=True)
class VerifiedPackage:
    verified: bool
    package: BuiltPackage
    target: Address
    process: FallibleProcessResult


class PytoolingVerifyRequest(VerifyRequest):
    pass


class PytoolingVerifyTarget(VerifyTarget):
    alias = "pytooling_verify_distribution"
    help = "A verification."

    core_fields = (
        *VerifyTarget.core_fields,
        VerificationVerifier,
        VerificationBuildArtefacts,
    )
    verify_request_type = PytoolingVerifyRequest


@rule
async def pytooling_verify_distribution(
        request: PytoolingVerifyRequest) -> VerifiedPackage:
    paths = [artifact.relpath for artifact in request.package.artifacts]

    build_artefacts = await Get(
        Targets,
        UnparsedAddressInputs,
        request.target[VerificationBuildArtefacts].to_unparsed_address_inputs(package=request.fieldset.address.spec_path))

    print("BUILD ARTEFACTS")
    print(build_artefacts)

    verifier = await Get(
        Targets,
        UnparsedAddressInputs,
        request.target[VerificationVerifier].to_unparsed_address_inputs())
    resolved_entry_point, transitive_targets = await MultiGet(
        Get(ResolvedPexEntryPoint, ResolvePexEntryPointRequest(verifier[0][PexEntryPointField])),
        Get(TransitiveTargets, TransitiveTargetsRequest([verifier[0].address])))
    output_filename = "verifier.pex"
    pex = await Get(
        VenvPex,
        PexFromTargetsRequest(
            addresses=[verifier[0].address],
            internal_only=True,
            include_source_files=True,
            # additional_sources=request.target[VerificationVerifier].to_unparsed_address_inputs(),
            main=resolved_entry_point.val,
            output_filename=output_filename))
    process = await MultiGet(
        Get(FallibleProcessResult,
            VenvPexProcess(
                pex,
                argv=[str(request.fieldset.address.spec_path), path],
                input_digest=request.package.digest,
                description=f"Verifying {path} with {request.target.address}."))
        for path in paths)
    return VerifiedPackage(
        verified=not any(p.exit_code for p in process),
        process=process,
        package=request.package,
        target=request.target.address)


@frozen_after_init
@dataclass(unsafe_hash=True)
class VerifiedPackageSet:
    verifies: FrozenOrderedSet[VerifiedPackage]

    def __init__(self, verified_packages: Iterable[VerifiedPackage]):
        self.verifies = FrozenOrderedSet(verified_packages)


@goal_rule
async def verify(
        console: Console,
        targets: Targets,
        union_membership: UnionMembership) -> Verify:
    verifiable_targets: List[Tuple[Target, PackageFieldSet]] = []

    # Retrieve verifiable targets and their package type.
    for target in targets:
        if VerifyTargetFieldSet.is_applicable(target):
            package_fieldset = _can_package(target, union_membership)
            if package_fieldset:
                verifiable_targets.append((target, package_fieldset))
            else:
                logger.warn(
                    f"Unable to verify {target.address} as it is not a packageable target."
                )
                return Verify(exit_code=1)

    verifiable_targets_set = await MultiGet(
        Get(Targets,
            UnparsedAddressInputs,
            verifiable[VerifyTargetField].to_unparsed_address_inputs())
        for (verifiable, _) in verifiable_targets)
    built_packages = await MultiGet(
        Get(BuiltPackage, PackageFieldSet, package_fieldset.create(target))
        for (target, package_fieldset) in verifiable_targets)
    verifiables = zip(
        verifiable_targets, verifiable_targets_set, built_packages)

    requests: List[VerifyRequest] = []

    verifiers = set()
    for (target, _), verify_targets, built_package in verifiables:
        verifiers = verifiers | set(verify_targets)
        for verify_target in verify_targets:
            fieldset = verify_target.verifyee_fieldset_type.create(target)
            # logger.info(f"Verifying {target.address} with {verify_target.address}")
            requests.append(
                verify_target.verify_request_type(
                    built_package,
                    fieldset,
                    verify_target))

    verification = await MultiGet(
        Get(VerifiedPackage, VerifyRequest, request) for request in requests)

    for result in verification:
        if not result.verified:
            console.print_stderr(f"{console.red('𐄂')}{result.target} Errors encountered.")
        else:
            console.print_stdout(f"{console.green('o')}{result.target} Success.")
            # print(result.process)
        for process in result.process:
            if not result.verified:
                console.print_stderr(f" {console.red('𐄂')}{result.target} Error encountered.")
                console.print_stderr(process.stderr.decode("utf-8"))
            else:
                console.print_stdout(f" {console.green('o')}{result.target} Success!.")
                console.print_stdout(process.stdout.decode("utf-8"))
    return Verify(exit_code=0)


def target_types():
    return [PytoolingVerifyTarget]


def rules():
    return (
        *collect_rules(),
        PytoolingDistribution.register_plugin_field(VerifyTargetField),
        UnionRule(VerifyRequest, PytoolingVerifyRequest))
