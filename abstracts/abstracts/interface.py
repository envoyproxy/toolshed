from abc import ABCMeta

from abstracts.implements import Implementer


class Interface(Implementer, ABCMeta):
    """Metaclass for implementers of interfaces."""
    pass
