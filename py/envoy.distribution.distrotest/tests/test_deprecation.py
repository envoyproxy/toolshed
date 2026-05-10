
import warnings

warnings.filterwarnings(
    "ignore",
    message="envoy\\.distribution\\.distrotest is deprecated.*",
    category=DeprecationWarning)

import envoy.distribution.distrotest as distrotest_mod  # noqa: E402


def test_distrotest_deprecation_warning_on_import():
    import importlib
    import warnings as w

    with w.catch_warnings(record=True) as caught:
        w.simplefilter("always", DeprecationWarning)
        importlib.reload(distrotest_mod)

    assert any(
        warning.category is DeprecationWarning
        and str(warning.message) == distrotest_mod.DEPRECATION_MESSAGE
        for warning in caught)
