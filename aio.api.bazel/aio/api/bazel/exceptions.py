
class BazelError(Exception):
    pass


class BazelQueryError(BazelError):
    pass


class BazelRunError(BazelError):
    pass
