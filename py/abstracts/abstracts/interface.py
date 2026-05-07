"""Interface metaclass.

`Abstraction` subclasses `Interface` so abstractions can be treated as
interfaces by metaclass checks, while `Implementer.is_interface`
intentionally filters abstractions out for strict interface-only flows.
"""

from abc import ABCMeta

from abstracts.implements import Implementer


class Interface(Implementer, ABCMeta):
    """Metaclass for pure interface classes.

    May only contain `@interfacemethod` definitions; methods can never
    be invoked directly.
    """

    pass
