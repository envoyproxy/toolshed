
from envoy.github.abstract import (
    AGithubRelease, AGithubReleaseAssets, AGithubReleaseManager)


def test_imports():
    assert AGithubRelease
    assert AGithubReleaseAssets
    assert AGithubReleaseManager
