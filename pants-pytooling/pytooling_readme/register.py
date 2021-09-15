
from .goal import rules as goal_rules
from .snippet import (
    target_types as snippet_target_types,
    rules as snippet_rules)


def target_types():
    return snippet_target_types()


def rules():
    return (
        *goal_rules(),
        *snippet_rules())
