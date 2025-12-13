
import pytest

from envoy.base.utils import interface


@pytest.mark.parametrize(
    "interface",
    [interface.IProtobufSet,
     interface.IProtobufValidator,
     interface.IProject,
     interface.IInventories,
     interface.IChangelogs,
     interface.IChangelog,
     interface.IChangelogEntry])
async def test_interfaces(iface, interface):
    await iface(interface).check()
