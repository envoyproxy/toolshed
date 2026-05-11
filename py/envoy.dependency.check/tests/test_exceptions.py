
from envoy.dependency.check import exceptions


def test_exceptions_dependency_metadata_error():
    assert issubclass(exceptions.DependencyMetadataError, Exception)
    err = exceptions.DependencyMetadataError("some message")
    assert str(err) == "some message"
