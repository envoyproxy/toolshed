
from typing import Type

from aio.api import nist


class CPE(nist.ACPE):
    pass


class CVE(nist.ACVE):
    pass


class CVEMatcher(nist.ACVEMatcher):
    pass


class NISTDownloader(nist.ANISTDownloader):

    @property
    def parser_class(self) -> Type[nist.ANISTParser]:
        return NISTParser


class NISTParser(nist.ANISTParser):

    @property
    def cpe_class(self) -> Type[nist.ACPE]:
        return CPE

    @property
    def cve_class(self) -> Type[nist.ACVE]:
        return CVE

    @property
    def matcher_class(self) -> Type[nist.ACVEMatcher]:
        return CVEMatcher
