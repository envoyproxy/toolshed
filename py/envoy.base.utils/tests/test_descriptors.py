from envoy.base.utils.descriptors import classproperty


def test_classproperty_access_via_class() -> None:
    class Example:
        seen_cls = None

        @classproperty
        def value(cls) -> int:
            Example.seen_cls = cls
            return 42

    assert Example.value == 42
    assert Example.seen_cls is Example


def test_classproperty_access_via_instance() -> None:
    class Example:
        seen_cls = None

        @classproperty
        def value(cls) -> int:
            Example.seen_cls = cls
            return 7

    instance = Example()

    assert instance.value == 7
    assert Example.seen_cls is Example


def test_classproperty_propagates_docstring() -> None:
    class Example:
        @classproperty
        def value(cls) -> int:
            """Example docstring."""
            return 1

    assert Example.__dict__["value"].__doc__ == "Example docstring."
