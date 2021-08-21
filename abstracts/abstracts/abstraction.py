from abc import ABCMeta

from abstracts.implements import Implementer


class Abstraction(Implementer, ABCMeta):
    pass
