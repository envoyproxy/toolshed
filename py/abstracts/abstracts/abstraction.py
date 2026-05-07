from __future__ import annotations

"""Abstraction metaclass.

`Abstraction` extends `Interface`, so abstractions are still recognized as
interfaces by `isinstance` checks while `Implementer.is_interface` can
deliberately exclude abstractions.
"""

from abstracts.interface import Interface


class Abstraction(Interface):
    """Metaclass for abstract classes.

    An `Abstraction` may contain both `@abstractmethod` and
    `@interfacemethod` definitions.
    """

    pass
