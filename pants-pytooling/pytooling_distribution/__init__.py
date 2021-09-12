"""pytooling_distribution plugin."""

from pants.backend.python.goals.setup_py import SetupKwargsRequest
from pants.backend.python.target_types import PythonDistribution
from pants.engine.target import Target


class PytoolingSetupKwargsRequest(SetupKwargsRequest):

    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        return isinstance(target, PytoolingDistribution)


class PytoolingDistribution(Target):
    """Pytooling distribution."""
    help = "Pytooling distribution"
    alias = "pytooling_distribution"
    core_fields = PythonDistribution.core_fields
