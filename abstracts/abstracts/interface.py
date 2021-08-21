from abc import ABCMeta

from abstracts.implements import Implementer


class Interface(Implementer, ABCMeta):
    pass
