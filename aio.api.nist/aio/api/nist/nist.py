
from typing import Type

import abstracts

from aio.api import nist


@abstracts.implementer(nist.ACPE)
class CPE:
    pass


@abstracts.implementer(nist.ACVE)
class CVE:
    pass


@abstracts.implementer(nist.ACVEMatcher)
class CVEMatcher:
    pass


@abstracts.implementer(nist.ANISTDownloader)
class NISTDownloader:

    @property
    def parser_class(self) -> Type[nist.ANISTParser]:
        return NISTParser


@abstracts.implementer(nist.ANISTParser)
class NISTParser:

    @property
    def cpe_class(self) -> Type[nist.ACPE]:
        return CPE

    @property
    def cve_class(self) -> Type[nist.ACVE]:
        return CVE

    @property
    def matcher_class(self) -> Type[nist.ACVEMatcher]:
        return CVEMatcher
