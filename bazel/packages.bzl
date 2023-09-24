load("@python3_11//:defs.bzl", "interpreter")
load("@rules_python//python:pip.bzl", "pip_parse")
load("//:versions.bzl", "VERSIONS")

def load_packages():
    # This is empty - it should be overridden in your repo
    pip_parse(
        name = "pip3",
        requirements_lock = "@envoy_toolshed//:requirements.txt",
        python_interpreter_target = interpreter,
    )
