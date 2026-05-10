"""Fuzz the EnvoyLoader YAML loader (envoy.base.utils.yaml).

Atheris harness — not part of any published package.

Usage (local):
    pip install atheris
    python py/tools/fuzzing/fuzz_yaml.py -atheris_runs=100000
"""

import sys

import atheris

with atheris.instrument_imports():
    import yaml

    from envoy.base.utils.yaml import EnvoyLoader


def TestOneInput(data: bytes) -> None:
    """Feed raw bytes to the EnvoyLoader.

    Expected / benign exceptions are caught so the fuzzer only stops for
    truly unexpected failures.
    """
    try:
        text = data.decode("utf-8", errors="replace")
        yaml.load(text, Loader=EnvoyLoader)
    except yaml.YAMLError:
        # Malformed YAML — expected; not a bug.
        pass
    except MemoryError:
        # Extremely large allocations from crafted input — expected.
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
