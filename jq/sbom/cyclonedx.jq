# CycloneDX SBOMs from dependency metadata.
#
# The input is an object of dependencies keyed by name, as for the CVE scanner
# (`cve::nvd_scan`), where each may have:
#
#   version                          (required: without one it is not listed)
#                                    A Bazel registry suffix (`.bcr.1`, `.envoy`) is not part
#                                    of the upstream version, see `upstream_version`.
#   project_name, project_desc, project_url
#   license, license_url
#   cpe                              ("N/A" for none)
#   source.url or urls: [...]        (where it is downloaded from)
#   sha256 (hex) or source.integrity (SRI, eg "sha256-<base64>")

def _base64_alphabet:
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

# Hex of a base64 string. jq's `@base64d` decodes to text, so cannot be used for a digest.
def base64_hex:
  _base64_alphabet as $alphabet
  | sub("=+$"; "")
  | [explode[]
     | ([.] | implode) as $char
     | ($alphabet | index($char) // error("not base64: \($char)"))
     | . as $value
     | range(5; -1; -1)
     | ($value / pow(2; .) | floor) % 2]
  | . as $bits
  | [range(0; ($bits | length) - 7; 8)
     | $bits[. : . + 8]
     | reduce .[] as $bit (0; . * 2 + $bit)
     | "0123456789abcdef"[. / 16 | floor : (. / 16 | floor) + 1]
       + "0123456789abcdef"[. % 16 : . % 16 + 1]]
  | join("");

# Where a dependency is downloaded from, or null: the source archive of a module if there is
# one, as its `urls` are those of the module in its registry.
def download_url:
  .source.url // (.urls // [])[0] // null;

# A version without the suffixes of a Bazel registry, which version its packaging of an
# upstream release: `1.2.3.bcr.1`, `1.2.3.envoy`, `1.2.3.bcr.envoy.2` are all upstream `1.2.3`.
def upstream_version:
  tostring | sub("([.](bcr|envoy)([.][0-9]+)?)+$"; "");

# CycloneDX `hashes` for a dependency: `sha256` as hex, or `source.integrity` as SRI.
def hashes:
  if ((.sha256 // "") | test("^[0-9a-fA-F]{64}$")) then
    [{alg: "SHA-256", content: (.sha256 | ascii_downcase)}]
  else
    ((if ((.sha256 // "") | test("^sha(256|384|512)-")) then .sha256 else .source.integrity end) // "")
    | capture("^sha(?<bits>256|384|512)-(?<digest>[A-Za-z0-9+/]+=*)$")? // null
    | if . then [{alg: "SHA-\(.bits)", content: (.digest | base64_hex)}] else [] end
  end;

# A package URL: `pkg:github/<owner>/<repo>@<version>` for a GitHub download, else
# `pkg:generic/<name>@<version>` with the download URL.
def purl($name):
  (.version | upstream_version | @uri) as $version
  | download_url as $url
  | (($url // "")
     | capture("^https://github[.]com/(?<owner>[^/]+)/(?<repo>[^/]+)/")? // null) as $github
  | if $github then
      "pkg:github/\($github.owner | ascii_downcase)/\($github.repo | ascii_downcase)@\($version)"
    else
      "pkg:generic/\($name | @uri)@\($version)"
      + if $url then "?download_url=\($url | @uri)" else "" end
    end;

# SPDX license ids recognized by `licenses`, in their canonical case. CycloneDX only accepts a
# listed SPDX id as a license `id`; anything else is given as a license `name`.
def spdx_ids:
  [
    "0BSD", "Apache-1.1", "Apache-2.0", "Artistic-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "BSD-3-Clause-Clear", "BSD-4-Clause", "BSL-1.0", "bzip2-1.0.6", "CC-BY-4.0", "CC0-1.0", "curl",
    "EPL-2.0", "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0", "GPL-3.0-only",
    "GPL-3.0-or-later", "ICU", "ISC", "LGPL-2.0", "LGPL-2.0-only", "LGPL-2.0-or-later", "LGPL-2.1",
    "LGPL-2.1-only", "LGPL-2.1-or-later", "LGPL-3.0", "LGPL-3.0-only", "LGPL-3.0-or-later",
    "libpng-2.0", "MIT", "MIT-0", "MPL-1.1", "MPL-2.0", "NCSA", "OpenSSL", "PostgreSQL",
    "Python-2.0", "Unicode-3.0", "Unicode-DFS-2016", "Unlicense", "UPL-1.0", "WTFPL", "X11", "Zlib"
  ];

# CycloneDX `licenses`: an SPDX expression if it has an operator, an SPDX id if it is one of
# `spdx_ids` (in any case), else a named license.
def licenses:
  (.license // "") as $license
  | (.license_url // null) as $url
  | if $license == "" then
      []
    elif ($license | test(" (AND|OR|WITH) ")) then
      [{expression: $license}]
    else
      (first(spdx_ids[] | select(ascii_downcase == ($license | ascii_downcase))) // null) as $id
      | [{license: (
            (if $id then {id: $id} else {name: $license} end)
            + if $url then {url: $url} else {} end)}]
    end;

def external_references:
  [
    (.project_url // null | select(.) | {type: "website", url: .}),
    (download_url | select(.) | {type: "distribution", url: .})
  ];

# A CycloneDX component for the dependency called `$name`. Its version is the upstream one; a
# different Bazel registry version is given as the `bazel:module_version` property.
def component($name):
  purl($name) as $purl
  | (.version | tostring) as $version
  | {
      type: "library",
      "bom-ref": $purl,
      name: (.project_name // $name),
      version: (.version | upstream_version),
      purl: $purl,
    }
  + (if .project_desc then {description: .project_desc} else {} end)
  + (if ((.cpe // "N/A") | . != "N/A" and startswith("cpe:")) then {cpe: .cpe} else {} end)
  + (licenses | if length > 0 then {licenses: .} else {} end)
  + (hashes | if length > 0 then {hashes: .} else {} end)
  + (external_references | if length > 0 then {externalReferences: .} else {} end)
  + (if (.version | upstream_version) != $version then
       {properties: [{name: "bazel:module_version", value: $version}]}
     else {} end);

# Only the dependencies that a reachability map (`//dependency:reachability.bzl`) has as
# reached in production. A dependency is matched to the map's repository names by its key, or
# by its `apparent_name` or `module_name` where those differ.
def reachable($reachability):
  ([$reachability.dependencies // {} | .[] | select(.production) | .name] | unique) as $names
  | with_entries(
      select(
        [.key, .value.apparent_name, .value.module_name]
        | map(select(. != null) | . as $name | $names | index($name))
        | any));

# Whether a dependency is only used to build, by its categories: `$options.build_categories`
# lists the categories that mean so, and a dependency with any of them is build-time (it may
# have others too). `$options.category_key` names the field with a dependency's categories
# (`use_category` by default). Without `build_categories` nothing is build-time.
def build_time($options):
  ($options.build_categories // []) as $categories
  | (.[$options.category_key // "use_category"] // []) as $have
  | any($have[]; . as $category | $categories | index($category));

# A CycloneDX 1.5 BOM of the dependencies, for the application described by `$subject`:
#
#   {name: ..., version: ..., purl: (optional), description: (optional), timestamp: (optional)}
#
# `$options` says what to do with build-time dependencies (see `build_time`):
#
#   {build_categories: [...], category_key: "use_category", build_time: "omit"}
#
# where `build_time` is one of:
#
#   omit      leave them out (the default)
#   excluded  list them with the `excluded` scope: used to build, not part of what is built
#   include   list them as any other component
#
# Components are sorted by name. There is no serial number, and no timestamp unless one is
# given, so that the same input gives the same output.
def bom($subject; $options):
  ($subject.purl // "pkg:generic/\($subject.name | @uri)@\($subject.version | tostring | @uri)") as $ref
  | ($options.build_time // "omit") as $mode
  | if (["omit", "excluded", "include"] | index($mode)) then .
    else error("sbom: unknown build_time: \($mode)") end
  | [to_entries[]
     | select(.value.version != null)
     | .key as $name
     | .value
     | build_time($options) as $build
     | select(($build and $mode == "omit") | not)
     | component($name)
       + if $build and $mode == "excluded" then {scope: "excluded"} else {} end]
  | sort_by(.name, .["bom-ref"]) as $components
  | {
      bomFormat: "CycloneDX",
      specVersion: "1.5",
      version: 1,
      metadata: (
        (if $subject.timestamp then {timestamp: $subject.timestamp} else {} end)
        + {component: (
            {
              type: "application",
              "bom-ref": $ref,
              name: $subject.name,
              version: ($subject.version | tostring),
              purl: $ref,
            }
            + if $subject.description then {description: $subject.description} else {} end)}),
      components: $components,
      dependencies: [{
        ref: $ref,
        dependsOn: ($components | map(select(.scope != "excluded") | .["bom-ref"]) | unique),
      }],
    };

def bom($subject):
  bom($subject; {});
