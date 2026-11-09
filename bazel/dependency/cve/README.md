# CVE scanner

Scan raw dependency metadata against NVD 2.0 JSON data and CVE Program
(cvelistV5) records:

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

## WORKSPACE setup

On this branch the scanner is loaded through WORKSPACE:

- `setup_sq()` (`//pgp:repositories.bzl`) creates `@envoy_toolshed_jq`, which
  provides the `cve/*` jq modules, a `jq` executable with them importable and
  `toolshed_jq`. jq itself comes from the `aspect_bazel_lib` toolchain.
- `load_packages()` (`//:packages.bzl`) creates the `cve_pip3` hub for the
  data fetchers. Scanning only needs the hub to exist; running
  `<name>.update` also needs its `install_deps()`:

```starlark
load("@cve_pip3//:requirements.bzl", cve_install_deps = "install_deps")

cve_install_deps()
```

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
- `urls`, `project_url`, `license_url` (optional): the first `github.com`
  url among them supplies an `owner`/`repo` name for matching CVE Program
  records (see below), alongside the CPE vendor/product.
- Additional fields are ignored.

This is a potential-vulnerability detector, not a proof of exploitability:
it matches vendor/product/version and publication dates, rather than
evaluating the complete NVD configuration logic.

## CVE Program records

NVD only adds CPE configurations when it analyzes a CVE. A large share of
recently published CVEs never get there (`Awaiting Analysis`, `Received`, or
`Deferred`, which NVD will not analyze), so CPE matching alone misses them
regardless of the CPEs tracked. The CVE Program record published by the CNA
carries the affected versions from day one, so the scanner also matches those.

`<name>.update` fetches the latest
[cvelistV5](https://github.com/CVEProject/cvelistV5/releases) release archive
and writes compacted `PUBLISHED` records published from `start_year` (by
publication date, not the year in the id) to `cvelist/YYYY-MM.json` under the
data directory, keyed by publication month like the NVD files. The whole set is refetched on every update: records are
amended in place and the archive is a single download. Consumers must glob
the subdirectory into `cve_data` (and sync it, eg `gsutil rsync -r`):

```starlark
filegroup(
    name = "cve-data-dir",
    srcs = glob([
        "cve_data/*.json",
        "cve_data/cvelist/*.json",
    ]),
)
```

Records match on the CNA/ADP asserted `vendor`/`product` (against the CPE
vendor/product, the CPE vendor without any `_project` suffix, or the github
owner/repo) or on `cpes` where an ADP has supplied them (including any
version in the CPE), and on the asserted version entries
(`lessThan`/`lessThanOrEqual` ranges, wildcard limits such as `2.5.*`,
free-text `< x` / `>= x, < y` constraints, single versions, `changes[]` and
`defaultStatus`; see the jq README for the precedence rules).

The scan is the union of both sources: matches are merged by CVE id, each
carries `sources` (`nvd`, `cna`) and each matched dependency its `source`.
A CVE matched only from its CVE Program record also records whether NVD has
analyzed it (`nvd_analyzed`): `false` means NVD has no CPE data for it yet
(or, if `Deferred`, ever); `true` means NVD's CPE configurations did not
match the tracked tags, which may be worth checking. Both fail `<name>.test`
like any match; use `ignored_cves` for false positives.

## Configuration and data

`config` is YAML:

```yaml
start_year: 2024
ignored_cves:
- CVE-2024-1234
sources: [nvd, cna]
```

`start_year` is an integer, the first publication year fetched.
`ignored_cves` is a list of CVE IDs (defaults to empty).
`sources` selects the data scanned, `nvd` (NVD CPE configurations) and/or
`cna` (CVE Program records, see above); default both.

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

The cvelist fetcher resolves the latest release through the GitHub API. To
authenticate (avoiding the unauthenticated rate limits) pass a token into
the fetch action, which does not inherit the shell environment:

```bash
GITHUB_TOKEN=... bazel run //tools/dependency:cves.update \
  --action_env=CVE_UPDATE_NONCE="$(date +%s%N)" \
  --action_env=GITHUB_TOKEN
```

The fetchers use `aiohttp` and `aio.run.runner` via the `cve_pip3` hub.
TODO(phlax): Decide its long-term home: Python brings a toolchain into
consumers' graphs (slow); consider a hermetic curl + jq paging/backoff loop,
or a prebuilt fetcher.
