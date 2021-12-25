
import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubLabel)
class DummyGithubLabel:
    pass


def test_abstract_label_constructor(patches):
    args = tuple(f"ARG{i}" for i in range(0, 3))
    kwargs = {f"K{i}": f"V{i}" for i in range(0, 3)}
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.label")

    with patched as (m_super, ):
        m_super.return_value = None
        label = DummyGithubLabel(*args, **kwargs)

    assert isinstance(label, github.abstract.base.GithubRepoEntity)
    assert (
        list(m_super.call_args)
        == [args, kwargs])
