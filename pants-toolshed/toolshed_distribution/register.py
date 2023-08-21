
from . import PytoolingDistribution
from . import my_rules


def target_types():
    return [PytoolingDistribution]


def rules():
    return my_rules.rules()
