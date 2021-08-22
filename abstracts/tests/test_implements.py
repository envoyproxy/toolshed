from random import random
from unittest.mock import MagicMock

import pytest

import abstracts


def test_implementer_constructor():
    with pytest.raises(TypeError):
        abstracts.Implementer()

    assert issubclass(abstracts.Implementer, type)


@pytest.mark.parametrize("isinst", [True, False])
def test_implementer_abstract_info(patches, isinst):
    abstract_methods = [f"METHOD{i}" for i in range(0, 5)]
    abstract_class = MagicMock()
    abstract_class.__abstractmethods__ = abstract_methods
    abstract_class.__name__ = MagicMock()

    patched = patches(
        "isinstance",
        prefix="abstracts.implements")

    with patched as (m_inst, ):
        m_inst.return_value = isinst
        if not isinst:
            with pytest.raises(TypeError) as e:
                abstracts.Implementer.abstract_info(abstract_class)
            assert (
                e.value.args[0]
                == ("Implementers can only implement subclasses of "
                    "`abstracts.Abstraction`, unrecognized: "
                    f"'{abstract_class}'"))
        else:
            assert (
                abstracts.Implementer.abstract_info(abstract_class)
                == (f"{abstract_class.__module__}.{abstract_class.__name__}",
                    abstract_class.__doc__,
                    abstract_methods))


@pytest.mark.parametrize(
    "methods",
    [[],
     [f"METHOD{i}" for i in range(0, 2)],
     [f"METHOD{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "has_docs",
    [[],
     [f"METHOD{i}" for i in range(0, 2)],
     [f"METHOD{i}" for i in range(0, 5)]])
@pytest.mark.parametrize(
    "is_classmethod",
    [[],
     [f"METHOD{i}" for i in range(0, 2)],
     [f"METHOD{i}" for i in range(0, 5)]])
@pytest.mark.parametrize("doc", [True, False])
def test_implementer_add_docs(patches, methods, has_docs, doc, is_classmethod):
    abstract_docs = {f"DOC{i}": int(random() * 10) for i in range(0, 5)}
    abstract_methods = {f"METHOD{i}": MagicMock() for i in range(0, 5)}

    clsdict = MagicMock()
    klass = MagicMock()

    if not doc:
        klass.__doc__ = ""

    for method, abstract_klass in abstract_methods.items():
        getattr(abstract_klass, method).__doc__ = "KLASS DOCS"
        if method not in methods:
            delattr(klass, method)
            continue
        if method not in has_docs:
            getattr(klass, method).__doc__ = ""
        if method in is_classmethod:
            getattr(klass, method).__self__ = "CLASSMETHOD_CLASS"

    patched = patches(
        "Implementer.implementation_info",
        prefix="abstracts.implements")

    with patched as (m_info, ):
        m_info.return_value = abstract_docs, abstract_methods
        assert not abstracts.Implementer.add_docs(clsdict, klass)

    assert (
        klass.__doc__
        == (MagicMock.__doc__
            if doc
            else "\n".join(
                    f"Implements: {k}\n{v}\n"
                    for k, v in abstract_docs.items())))

    for abstract_method, abstract_klass in abstract_methods.items():
        if abstract_method not in methods:
            continue
        expected = MagicMock.__doc__
        no_docs = (
            abstract_method in is_classmethod
            and abstract_method not in has_docs)
        if no_docs:
            expected = ""
        elif abstract_method not in has_docs:
            expected = "KLASS DOCS"
        assert (
            getattr(klass, abstract_method).__doc__
            == expected)


@pytest.mark.parametrize(
    "subc", [(), ("A", "B", "C"), ("A", "C"), ("D", "E")])
@pytest.mark.parametrize(
    "missing", [(), ("A", "B", "C"), ("A", "C"), ("D", "E")])
def test_implementer_add_interfaces(patches, subc, missing):
    patched = patches(
        "dir",
        "issubclass",
        prefix="abstracts.implements")

    mock_register = MagicMock()
    mock_init = MagicMock()

    class DummyInterface:

        def __init__(self, x):
            mock_init(x)
            self.x = x
            count = (7 if x in missing else 5)
            self.__abstractmethods__ = set(
                f"METHOD{i}" for i in range(0, count))

        def register(self, klass):
            mock_register(self.x, klass)

    ifaces = [DummyInterface(x) for x in ["A", "B", "C"]]

    def mock_dir(klass):
        return set(f"METHOD{i}" for i in range(0, 5))

    def mock_subclass(klass, iface):
        return iface.x in subc

    missing_ifaces = tuple(
        x for x in missing
        if (x in ["A", "B", "C"]
            and x not in subc))

    with patched as (m_dir, m_subc):
        m_dir.side_effect = mock_dir
        m_subc.side_effect = mock_subclass
        if missing_ifaces:
            with pytest.raises(TypeError) as e:
                abstracts.Implementer.add_interfaces(ifaces, "KLASS")
        else:
            assert not abstracts.Implementer.add_interfaces(ifaces, "KLASS")

    if not missing_ifaces:
        assert (
            list(list(c) for c in m_subc.call_args_list)
            == [[('KLASS', iface), {}] for iface in ifaces])
        assert (
            list(list(c) for c in mock_register.call_args_list)
            == [[(iface.x, 'KLASS', ), {}]
                for iface in ifaces if iface.x not in subc])
        return

    failed_index = ('A', 'B', 'C').index(missing_ifaces[0])
    failed = ifaces[failed_index]
    assert (
        e.value.args[0]
        == (f"Not all methods for interface {failed} "
            "provided: missing ['METHOD5', 'METHOD6']"))
    assert (
        list(list(c) for c in m_subc.call_args_list)
        == [[('KLASS', iface), {}] for iface in ifaces[:failed_index + 1]])
    assert (
        list(list(c) for c in mock_register.call_args_list)
        == [[(iface.x, 'KLASS', ), {}]
            for iface in ifaces[:failed_index] if iface.x not in subc])


@pytest.mark.parametrize("attrs", [(), ("A", "B", "C"), ("A", "C")])
@pytest.mark.parametrize("methods", [(), ("A", "B", "C"), ("A", "C")])
def test_implementer_check_interface(patches, attrs, methods):
    clsdict = dict(FOO="BAR")
    patched = patches(
        "Implementer.get_class_attrs",
        "Implementer.get_interface_methods",
        prefix="abstracts.implements")

    with patched as (m_attrs, m_methods):
        m_attrs.return_value = set(attrs)
        m_methods.return_value = set(methods)
        extra = set(attrs) - set(methods)
        if extra:
            with pytest.raises(TypeError) as e:
                abstracts.Implementer.check_interface(clsdict)
        else:
            abstracts.Implementer.check_interface(clsdict)

    assert (
        list(m_attrs.call_args)
        == [(clsdict, ), {}])
    assert (
        list(m_methods.call_args)
        == [(clsdict, ), {}])
    if extra:
        assert (
            e.value.args[0]
            == ("Interfaces can only contain methods decorated with "
                f"`@interfacemethod`: got {extra}"))


@pytest.mark.parametrize("bases", [(), ("A", "B", "C"), ("A", "C")])
@pytest.mark.parametrize("implements", [(), ("A", "B", "C"), ("A", "C")])
@pytest.mark.parametrize("abstraction", [None, "A", "B", "C"])
def test_implementer_get_bases(patches, bases, implements, abstraction):
    clsdict = dict(__implements__=implements)
    patched = patches(
        "Implementer.is_interface",
        prefix="abstracts.implements")

    def mock_isiface(item):
        return item != abstraction

    with patched as (m_isiface, ):
        m_isiface.side_effect = mock_isiface
        assert (
            abstracts.Implementer.get_interfaces(bases, clsdict)
            == tuple(
                x for x
                in clsdict["__implements__"]
                if x not in bases
                and x != abstraction))


def test_implementer_get_class_attrs():
    clsdict = (
        ["__NOTME{i}" for i in range(0, 5)]
        + ["ME__{i}" for i in range(0, 5)])
    assert (
        abstracts.Implementer.get_class_attrs(clsdict)
        == set(["ME__{i}" for i in range(0, 5)]))


def test_implementer_get_interface_methods(patches):
    patched = patches(
        "isinstance",
        prefix="abstracts.implements")

    class DummyPropertyGetter:

        def __init__(self, prop_iface):
            if prop_iface is not None:
                self.__isinterfacemethod__ = prop_iface

    class DummyProperty:

        def __init__(self, is_iface, amprop, prop_iface):
            self.amprop = amprop
            self.prop_iface = prop_iface
            if is_iface is not None:
                self.__isinterfacemethod__ = is_iface

        @property
        def fget(self):
            return DummyPropertyGetter(self.prop_iface)

    def mock_isinstance(item, klass):
        return item.amprop

    amprop = [True, False]
    prop_iface = [None, True, False]
    is_iface = [None, True, False]
    prop_values = []
    expected = []
    i = 0
    for v1 in is_iface:
        for v2 in amprop:
            for v3 in prop_iface:
                if v1 or (v2 and v3):
                    expected.append(i)
                prop_values.append((v1, v2, v3))
                i += 1
    props = {
        f"ITEM{i}": DummyProperty(*args)
        for i, args in enumerate(prop_values)}

    with patched as (m_inst, ):
        m_inst.side_effect = mock_isinstance
        assert (
            abstracts.Implementer.get_interface_methods(props)
            == set(f"ITEM{x}" for x in expected))


@pytest.mark.parametrize("bases", [(), ("A", "B", "C"), ("A", "C")])
@pytest.mark.parametrize("implements", [(), ("A", "B", "C"), ("A", "C")])
@pytest.mark.parametrize("abstraction", [None, "A", "B", "C"])
def test_implementer_get_interfaces(patches, bases, implements, abstraction):
    clsdict = dict(__implements__=implements)
    patched = patches(
        "isinstance",
        prefix="abstracts.implements")

    def mock_isinstance(item, klasses):
        return item != abstraction

    with patched as (m_inst, ):
        m_inst.side_effect = mock_isinstance
        assert (
            abstracts.Implementer.get_bases(bases, clsdict)
            == bases + tuple(
                x for x
                in clsdict["__implements__"]
                if x not in bases
                and x != abstraction))


@pytest.mark.parametrize("has_docs", ["odd", "even"])
def test_implementer_implementation_info(patches, has_docs):
    patched = patches(
        "Implementer.abstract_info",
        prefix="abstracts.implements")

    def iter_implements():
        for x in range(0, 5):
            yield f"ABSTRACT{x}"

    implements = list(iter_implements())
    clsdict = dict(__implements__=implements)

    def abstract_info(abstract):
        x = int(abstract[-1])
        methods = [f"METHOD{i}" for i in range(0, x + 1)]
        docs = (
            x % 2
            if has_docs == "even"
            else not x % 2)
        return abstract, docs, methods

    with patched as (m_info, ):
        m_info.side_effect = abstract_info
        docs, methods = abstracts.Implementer.implementation_info(clsdict)

    def oddeven(i):
        return (
            i % 2
            if has_docs == "even"
            else not i % 2)

    assert docs == {f"ABSTRACT{i}": 1 for i in range(0, 5) if oddeven(i)}
    assert (
        methods
        == {f'METHOD{i}': f'ABSTRACT{i}' for i in range(0, 5)})


@pytest.mark.parametrize("has_implements", [True, False])
@pytest.mark.parametrize("is_interface", [True, False])
@pytest.mark.parametrize("interface_raises", [None, BaseException])
def test_implementer_dunder_new(
        patches, has_implements, is_interface, interface_raises):
    patched = patches(
        "super",
        "Implementer.add_docs",
        "Implementer.add_interfaces",
        "Implementer.is_interface",
        "Implementer.check_interface",
        "Implementer.get_bases",
        "Implementer.get_interfaces",
        prefix="abstracts.implements")
    bases = MagicMock()
    clsdict = dict(FOO="BAR")

    if has_implements:
        clsdict["__implements__"] = "IMPLEMENTS"

    mock_super = MagicMock()

    class Super:

        def __new__(cls, *args):
            mock_super(*args)
            if not args:
                return cls
            return "NEW"

    with patched as patchy:
        (m_super, m_docs, m_ifaces,
         m_isiface, m_checkiface, m_bases, m_getifaces) = patchy
        m_super.side_effect = Super
        m_isiface.return_value = is_interface
        if interface_raises:
            m_checkiface.side_effect = interface_raises
        if not has_implements and is_interface and interface_raises:
            with pytest.raises(interface_raises):
                abstracts.Implementer.__new__(
                    abstracts.Implementer, "NAME", bases, clsdict)
        else:
            assert (
                abstracts.Implementer.__new__(
                    abstracts.Implementer, "NAME", bases, clsdict)
                == "NEW")

    if has_implements:
        assert (
            list(m_getifaces.call_args)
            == [(bases, clsdict), {}])
        assert (
            list(m_docs.call_args)
            == [(clsdict, "NEW"), {}])
        assert not m_isiface.called
        assert not m_checkiface.called
        assert (
            list(list(c) for c in mock_super.call_args_list)
            == [[(), {}],
                [('NAME', m_bases.return_value,
                  {'FOO': 'BAR', '__implements__': 'IMPLEMENTS'}), {}]])
        assert (
            list(m_ifaces.call_args)
            == [(m_getifaces.return_value, "NEW"), {}])
        return
    assert not m_ifaces.called
    assert not m_docs.called
    assert not m_getifaces.called
    assert (
        list(list(c) for c in mock_super.call_args_list)
        == [[(), {}],
            [('NAME', bases,
              {'FOO': 'BAR'}), {}]])
    assert (
        list(m_isiface.call_args)
        == [("NEW", ), {}])
    if is_interface:
        assert (
            list(m_checkiface.call_args)
            == [(clsdict, ), {}])
    else:
        assert not m_checkiface.called
