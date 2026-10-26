load("@rules_python//python:pip.bzl", "compile_pip_requirements")

compile_pip_requirements(
    name = "requirements",
    src = "requirements.in",
    extra_args = ["--allow-unsafe", "--generate-hashes"],
    python_version = "3.12",
    requirements_txt = "requirements.txt",
    tags = ["requires-network"],
)
