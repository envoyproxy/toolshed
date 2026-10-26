# CVE scanner

## Python dependencies

From the `bazel/` workspace, update Python deps:
`bazel run //dependency/cve:requirements.update`.
The unpinned inputs are in `requirements.in`; `requirements.txt` is the generated
hashed lockfile. Do not edit its hashes by hand.

Update the website lockfile with `bazel run //website:requirements.update`.
Check both lockfiles with:

```bash
bazel test //dependency/cve:requirements.test //website:requirements.test
```

These tests are tagged `requires-network`, `no-remote-exec`, and `no-sandbox` by
rules_python: CI must allow local access to PyPI and artifact downloads.
Use the `.test` targets in CI; the deprecated `requirements_test` aliases are
tagged `manual` by rules_python and are not discovered as tests by Bazel 9.

Scan raw dependency metadata against NVD 2.0 JSON data:

```starlark
load("@envoy_toolshed//dependency/cve:macros.bzl", "cve_scan")

cve_scan(
    name = "cves",
    deps = ":cpe-dependencies",
    config = ":cve.yaml",
    cve_data = ":cve-data",
    cve_data_dir = "cve_data",
)
```

The signature is `cve_scan(name, deps, config, cve_data,
cve_data_dir = "cve_data", visibility = None,
target_compatible_with = ["@platforms//os:linux"])`. The compatibility
constraints apply to updates, not scans.

## Dependency JSON contract

`deps` is a single JSON object keyed by dependency name, **not** preprocessed
with `cve/utils::parse_deps`:

```json
{
  "widget": {
    "cpe": "cpe:2.3:a:example:widget:*:*:*:*:*:*:*:*",
    "version": "1.2.3",
    "release_date": "2024-01-01"
  }
}
```

- `cpe`: CPE 2.3 string identifying vendor and product. Use `"N/A"` or `null`
  to exclude a dependency. The macro parses CPEs and versions itself.
- `version`: string, either a semantic version or an opaque version such as
  a commit hash. Semantic versions support inclusive/exclusive NVD bounds;
  opaque versions use string comparison when bounds exist.
- `release_date`: ISO `YYYY-MM-DD` date. Dependencies released after a CVE's
  publication date are excluded, including hash-versioned dependencies.
- Additional fields are ignored.

This is a potential-vulnerability detector, not a proof of exploitability:
it matches vendor/product/version and publication dates, rather than
evaluating the complete NVD configuration logic.

## Configuration and data

`config` is YAML:

```yaml
start_year: 2024
ignored_cves:
- CVE-2024-1234
```

`start_year` is an integer, the first publication year fetched.
`ignored_cves` is a list of CVE IDs (defaults to empty).

`cve_data` supplies NVD 2.0 JSON files. A file may contain multiple consecutive
NVD page objects. Updates use filenames `YYYY-MM.json`. Non-JSON placeholders
are ignored; scanning an input with no JSON files fails with `No CVE data set`.
Normally consumers expose a `label_flag` selecting a placeholder by default
and a filegroup containing `glob(["cve_data/*.json"])` when enabled:

```bash
bazel test //tools/dependency:cves.test \
  --//tools/dependency:cve-data=//tools/dependency:cve-data-dir
```

Envoy can put this selection in `--config=cves`.

## Targets

- `<name>_deps`, `<name>_ignored`, `<name>_start_year`: parsed inputs.
- `<name>`: runnable scan, printing one JSON array to stdout.
- `<name>.scanned`: generates `<name>.scanned.json`. Missing data or invalid
  JSON fails the build; scan errors are deliberately not suppressed.
- `<name>.test`: passes for an empty array; otherwise prints the coloured
  report and exits 1.
- `<name>.update`: fetches data, then uses `write_source_files` to write the
  directory to package-relative `cve_data_dir`.

Helper targets and `<name>.test` are manual: invoke the test explicitly after
selecting a data set, rather than running it in wildcard test invocations.

```bash
bazel run //tools/dependency:cves.update \
  --action_env=CVE_UPDATE_NONCE="$(date +%s%N)" \
  --//tools/dependency:cve-data=//tools/dependency:cve-data-dir
```

Updates are manual, local, network-requiring actions, Linux-only by default,
with external caching disabled. Include a fresh `CVE_UPDATE_NONCE` action
environment value as above: Bazel's `no-cache` tag does not disable its local
action cache, so otherwise an unchanged input set can reuse a previous fetch.
The action inherits `--action_env` values and the nonce changes its action key.
Existing month files come exclusively from the declared `cve_data`
inputs: they are copied into the output tree and skipped by the fetcher,
except the current month, which is refreshed. To refetch all months:

```bash
bazel run //tools/dependency:cves.update \
  --action_env=CVE_UPDATE_NONCE="$(date +%s%N)" \
  --action_env=OVERWRITE_ALL_CVE_DATA=1
```

Select the data label on subsequent updates to preserve previous months.
No repository paths or `BUILD_WORKSPACE_DIRECTORY` are needed.

The fetcher uses `aiohttp` and `aio.run.runner` via the `cve_pip3` hub.
TODO(phlax): Decide its long-term home: Python brings a toolchain into
consumers' graphs (slow); consider a hermetic curl + jq paging/backoff loop,
or a prebuilt fetcher.
