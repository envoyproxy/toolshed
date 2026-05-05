"""Fuzz the EnvoyYaml YAML loader (envoy.base.utils.yaml).

Atheris harness — not part of any published package.

Usage (local):
    pip install atheris
    python py/tools/fuzzing/fuzz_yaml.py -atheris_runs=100000
"""

import sys

import atheris

with atheris.instrument_imports():
    import yaml

    from envoy.base.utils.yaml import EnvoyYaml

# Build the YAML module augmented with the Envoy !ignore tag exactly once, so
# each TestOneInput call does not re-register constructors.
_envoy_yaml = EnvoyYaml().yaml


def TestOneInput(data: bytes) -> None:
    """Feed raw bytes to the EnvoyYaml safe-loader.

    Expected / benign exceptions are caught so the fuzzer only stops for
    truly unexpected failures.
    """
    try:
        text = data.decode("utf-8", errors="replace")
        _envoy_yaml.safe_load(text)
    except yaml.YAMLError:
        # Malformed YAML — expected; not a bug.
        pass
    except MemoryError:
        # Extremely large allocations from crafted input — expected.
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
