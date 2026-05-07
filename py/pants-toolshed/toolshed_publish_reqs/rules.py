"""Synthetic publish requirements from setup.cfg.

This plugin removes the need for checked-in
``publish-requirements.in`` files. For each ``py/*/setup.cfg`` file, it reads
``[options] install_requires`` and
emits synthetic ``python_requirement`` targets in a synthetic BUILD path,
``py/<pkg>/BUILD.publish-reqs``.

``setup.cfg`` is the only source of truth for wheel install requirements.
Synthetic target names use ``_publish__<canonical_name>`` where
``canonical_name`` is derived from
``packaging.utils.canonicalize_name(requirement.name).replace('-', '_')`` and
then sanitized to ``[a-z0-9_]``.

Analogous Pants core examples:
- ``pants.backend.python.goals.lockfile.PythonSyntheticLockfileTargetsRequest``
- ``pants.backend.python.providers.pyenv.custom_install.rules.
   SyntheticPyenvTargetsRequest``
- ``pants.backend.terraform.goals.lockfiles.
   TerraformSyntheticLockfileTargetsRequest``
"""

import configparser
import os
from dataclasses import dataclass

from pants.engine.fs import PathGlobs
from pants.engine.internals.synthetic_targets import (
    SyntheticAddressMaps,
    SyntheticTargetsRequest,
)
from pants.engine.internals.target_adaptor import TargetAdaptor
from pants.engine.intrinsics import (
    digest_to_snapshot,
    get_digest_contents,
    path_globs_to_digest,
)
from pants.engine.rules import collect_rules, rule
from pants.engine.unions import UnionRule

from toolshed_setup_cfg import parse_options

from .names import _publish_req_target_name


@dataclass(frozen=True)
class ToolshedPublishReqsRequest(SyntheticTargetsRequest):
    path: str = SyntheticTargetsRequest.SINGLE_REQUEST_FOR_ALL_TARGETS


def _adaptors_for_install_requires(
        package_dir: str,
        install_requires: list[str]) -> tuple[TargetAdaptor, ...]:
    adaptors: list[TargetAdaptor] = []
    for req_str in install_requires:
        try:
            name = _publish_req_target_name(req_str)
        except Exception as exc:
            raise ValueError(
                f"Invalid requirement {req_str!r} in "
                f"{package_dir}/setup.cfg") from exc
        adaptors.append(
            TargetAdaptor(
                "python_requirement",
                name=name,
                requirements=[req_str],
                resolve="publish",
                __description_of_origin__=f"{package_dir}/setup.cfg",
            )
        )
    return tuple(adaptors)


@rule
async def toolshed_publish_reqs(
    request: ToolshedPublishReqsRequest,
) -> SyntheticAddressMaps:
    digest = await path_globs_to_digest(PathGlobs(["py/*/setup.cfg"]))
    snapshot = await digest_to_snapshot(digest)
    contents = await get_digest_contents(snapshot.digest)

    address_maps: list[tuple[str, tuple[TargetAdaptor, ...]]] = []

    for file_content in sorted(contents, key=lambda item: item.path):
        package_dir = os.path.dirname(file_content.path)
        config = configparser.ConfigParser()
        config.read_string(file_content.content.decode("utf-8"))

        install_requires = parse_options(config, package_dir).get(
            "install_requires", [])
        adaptors = _adaptors_for_install_requires(
            package_dir,
            install_requires)
        if adaptors:
            address_maps.append(
                (f"{package_dir}/BUILD.publish-reqs", adaptors))

    return SyntheticAddressMaps.for_targets_request(request, address_maps)


def rules():
    return [
        *collect_rules(),
        UnionRule(SyntheticTargetsRequest, ToolshedPublishReqsRequest),
    ]
