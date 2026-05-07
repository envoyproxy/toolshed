import sys
import types

import pytest


def _install_pants_stubs() -> None:
    pants = types.ModuleType("pants")
    engine = types.ModuleType("pants.engine")
    fs = types.ModuleType("pants.engine.fs")
    fs.PathGlobs = object
    internals = types.ModuleType("pants.engine.internals")
    synthetic_targets = types.ModuleType("pants.engine.internals.synthetic_targets")

    class _SyntheticAddressMaps:
        @classmethod
        def for_targets_request(cls, *_args, **_kwargs):
            return cls()

    class _SyntheticTargetsRequest:
        SINGLE_REQUEST_FOR_ALL_TARGETS = ""

    synthetic_targets.SyntheticAddressMaps = _SyntheticAddressMaps
    synthetic_targets.SyntheticTargetsRequest = _SyntheticTargetsRequest
    target_adaptor = types.ModuleType("pants.engine.internals.target_adaptor")
    target_adaptor.TargetAdaptor = object
    intrinsics = types.ModuleType("pants.engine.intrinsics")
    intrinsics.digest_to_snapshot = None
    intrinsics.get_digest_contents = None
    intrinsics.path_globs_to_digest = None
    rules = types.ModuleType("pants.engine.rules")
    rules.collect_rules = lambda: []
    rules.rule = lambda func: func
    unions = types.ModuleType("pants.engine.unions")
    unions.UnionRule = object

    sys.modules["pants"] = pants
    sys.modules["pants.engine"] = engine
    sys.modules["pants.engine.fs"] = fs
    sys.modules["pants.engine.internals"] = internals
    sys.modules["pants.engine.internals.synthetic_targets"] = synthetic_targets
    sys.modules["pants.engine.internals.target_adaptor"] = target_adaptor
    sys.modules["pants.engine.intrinsics"] = intrinsics
    sys.modules["pants.engine.rules"] = rules
    sys.modules["pants.engine.unions"] = unions


try:
    from toolshed_publish_reqs.rules import _publish_req_target_name
except ModuleNotFoundError:
    _install_pants_stubs()
    from toolshed_publish_reqs.rules import _publish_req_target_name


@pytest.mark.parametrize(
    ("req_str", "expected"),
    (
        ("aiohttp>=3.8.1", "_publish__aiohttp"),
        ("PyYAML", "_publish__pyyaml"),
        ("pytest-asyncio", "_publish__pytest_asyncio"),
        ("Foo.Bar_Baz", "_publish__foo_bar_baz"),
        ("package[extra]>=1.0", "_publish__package"),
        ("package; python_version >= '3.10'", "_publish__package"),
        ("foo----bar", "_publish__foo_bar"),
        ("  aiohttp>=3.8.1  ", "_publish__aiohttp"),
    ),
)
def test_publish_req_target_name(req_str: str, expected: str):
    assert _publish_req_target_name(req_str) == expected
