
import pytest

from aio.api import github


@pytest.mark.parametrize(
    "interface",
    [github.IGithubIterator,
     github.IGithubAPI,
     github.IGithubIssues,
     github.IGithubTrackedIssue,
     github.IGithubTrackedIssues])
async def test_interfaces(iface, interface):
    await iface(interface).check()
