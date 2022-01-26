
import pytest

import abstracts

from envoy.dependency import check


@abstracts.implementer(check.ADependencyCPE)
class DummyDependencyCPE:
    pass


@pytest.mark.parametrize("product", [None, "FOO"])
@pytest.mark.parametrize("version", [None, "BAR"])
def test_cpe_constructor(product, version):
    kwargs = dict()
    if product:
        kwargs["product"] = product
    if version:
        kwargs["version"] = version
    cpe = DummyDependencyCPE("PART", "VENDOR", **kwargs)
    assert cpe.part == "PART"
    assert cpe.vendor == "VENDOR"
    assert cpe.product == (product or "*")
    assert cpe.version == (version or "*")
    assert cpe.vendor_normalized == "cpe:2.3:PART:VENDOR:*:*"


@pytest.mark.parametrize(
    "text",
    ["", "a:b:c:x:y:z", "cpe:2.3:x",
     "cpe:2.3:a:x:y:z", "cpe:2.3:a:b:c:x:y:z"])
def test_cpe_cls_fromstring(text):
    components = text.split(':')
    raises = False
    if len(components) < 6:
        raises = True
    elif not text.startswith('cpe:2.3:'):
        raises = True
    if raises:
        with pytest.raises(check.exceptions.CPEError) as e:
            check.ADependencyCPE.from_string(text)
        assert (
            e.value.args[0]
            == f"CPE string ({text}) must be a valid CPE v2.3 string")
        return
    cpe = check.ADependencyCPE.from_string(text)
    assert cpe.part == components[2]
    assert cpe.vendor == components[3]
    assert cpe.product == components[4]
    assert cpe.version == components[5]


@pytest.mark.parametrize("product", [None, "FOO"])
@pytest.mark.parametrize("version", [None, "BAR"])
def test_cpe_dunder_str(product, version):
    kwargs = dict()
    if product:
        kwargs["product"] = product
    if version:
        kwargs["version"] = version
    cpe = DummyDependencyCPE("PART", "VENDOR", **kwargs)
    assert (
        str(cpe)
        == f"cpe:2.3:PART:VENDOR:{product or '*'}:{version or '*'}")
