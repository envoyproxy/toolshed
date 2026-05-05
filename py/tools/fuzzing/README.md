# toolshed fuzzing harnesses

This directory contains [Atheris](https://github.com/google/atheris)-based
fuzz harnesses for ad-hoc local fuzzing of toolshed Python utilities.

It is **intentionally not packaged or published** — it is not included in any
`py/*/pyproject.toml` or `setup.cfg`, and will never appear in a wheel or
sdist.

## Why this exists

The [OpenSSF Scorecard](https://securityscorecards.dev/) "Fuzzing" check
(alert [#14](https://github.com/envoyproxy/toolshed/security/code-scanning/14))
detects fuzzing by scanning for `import atheris` in `.py` files.  Adding a
real harness here flips the score from 0 → 10 while also providing a
runnable harness against the toolshed YAML-loading layer.

## Harnesses

| File | Target |
|---|---|
| `fuzz_yaml.py` | `envoy.base.utils.yaml.EnvoyYaml` — the custom YAML loader that registers the `!ignore` tag used throughout Envoy configs |

## Running locally

```bash
# Install Atheris (requires a libFuzzer-enabled Clang; see
# https://github.com/google/atheris#installation for details)
pip install atheris

# Run for a small budget (good for a smoke-test)
python py/tools/fuzzing/fuzz_yaml.py -atheris_runs=100000

# Or, from inside py/tools/fuzzing/:
python fuzz_yaml.py -atheris_runs=100000
```

Atheris will print coverage and corpus statistics to stderr.  The harness
treats `yaml.YAMLError` and `MemoryError` as *expected* exceptions and will
not report them as crashes.  Non-UTF-8 bytes are silently replaced
(`errors='replace'`) before parsing.  Only truly unexpected exceptions
(e.g. `AssertionError`, `TypeError`) will surface as findings.
