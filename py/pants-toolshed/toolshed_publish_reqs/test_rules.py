import pytest

from toolshed_publish_reqs.names import _publish_req_target_name


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
