
import warnings

warnings.filterwarnings(
    "ignore",
    message="envoy\\.github\\.abstract is deprecated.*",
    category=DeprecationWarning)

from envoy.github.abstract import (  # noqa: E402
    AGithubRelease, AGithubReleaseAssets, AGithubReleaseManager)


def test_imports():
    assert AGithubRelease
    assert AGithubReleaseAssets
    assert AGithubReleaseManager


def test_abstract_deprecation_warning_on_import():
    import importlib
    import warnings as w
    import envoy.github.abstract as abstract_mod

    with w.catch_warnings(record=True) as caught:
        w.simplefilter("always", DeprecationWarning)
        importlib.reload(abstract_mod)

    assert any(
        warning.category is DeprecationWarning
        and str(warning.message) == abstract_mod.DEPRECATION_MESSAGE
        for warning in caught)
