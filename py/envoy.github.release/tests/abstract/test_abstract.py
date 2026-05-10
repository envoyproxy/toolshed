
from envoy.github.abstract import (  # noqa: E402
    AGithubRelease, AGithubReleaseAssets, AGithubReleaseManager)


def test_imports():
    assert AGithubRelease
    assert AGithubReleaseAssets
    assert AGithubReleaseManager
