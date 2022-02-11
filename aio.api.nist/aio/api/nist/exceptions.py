
class NISTError(Exception):
    pass


class CPEError(NISTError):
    pass


class CVEError(NISTError):
    pass


class CVECheckError(NISTError):
    pass
