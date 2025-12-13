
import abstracts

from aio.api import github


@abstracts.implementer(github.AGithubLabel)
class DummyGithubLabel:
    pass


def test_abstract_label_constructor(iters, patches):
    args = iters(tuple, count=3)
    kwargs = iters(dict, count=3)
    patched = patches(
        "GithubRepoEntity.__init__",
        prefix="aio.api.github.abstract.label")

    with patched as (m_super, ):
        m_super.return_value = None
        label = DummyGithubLabel(*args, **kwargs)

    assert isinstance(label, github.abstract.base.GithubRepoEntity)
    assert (
        m_super.call_args
        == [args, kwargs])
    label.name = "LABEL_NAME"
    assert (
        str(label)
        == f"<{label.__class__.__name__} LABEL_NAME>")
