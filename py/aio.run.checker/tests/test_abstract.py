
from aio.run.checker import abstract, interface


def test_abstract_problems():
    problems = abstract.AProblems()
    assert isinstance(problems, interface.IProblems)
    assert problems.warnings == []
    assert problems.errors == []
    assert "warnings" not in problems.__dict__
    assert "errors" not in problems.__dict__


def test_abstract_problems_warnings():
    problems = abstract.AProblems(warnings="WARNINGS")
    assert problems.warnings == "WARNINGS"
    assert problems.errors == []
    assert "warnings" not in problems.__dict__
    assert "errors" not in problems.__dict__


def test_abstract_problems_errors():
    problems = abstract.AProblems(errors="ERRORS")
    assert problems.errors == "ERRORS"
    assert problems.warnings == []
    assert "errors" not in problems.__dict__
    assert "warnings" not in problems.__dict__
