"""Build-graph reachability data for external dependencies.

Provides an aspect + rule that emit a JSON "reachability map" describing, for
every external repository reachable from a set of root targets, which targets
actually reach it - with enough fidelity to validate dependency metadata (eg
envoy's `deps.yaml` `use_category` markings) without any `bazel query`
scraping or shelling out.

The aspect runs inside the analysis graph, so it is bzlmod-native by
construction: it sees canonical repository names directly and attributes each
external dependency to the exact consuming target.

Usage:

```starlark
load("@envoy_toolshed//dependency:reachability.bzl", "dependency_reachability")

dependency_reachability(
    name = "dep-reachability",
    roots = ["//source/exe:envoy_main_common_with_core_extensions_lib"],
)

sh_test(
    name = "validate_deps",
    srcs = ["validate_deps.sh"],
    data = [":dep-reachability", "//bazel:deps.yaml"],
)
```

Building the target writes `<name>.json`:

```json
{
  "dependencies": {
    "<canonical repo name>": {
      "name": "<apparent/module name>",
      "production": true,
      "reached_by": [
        {"root": "//source/exe:envoy_main_common_with_core_extensions_lib", "production": true}
      ],
      "targets": ["@repo//pkg:target"],
      "consumers": [
        {
          "target": "//pkg:consumer",
          "repo": "",
          "testonly": false,
          "attrs": ["deps"],
          "roots": ["//source/exe:envoy_main_common_with_core_extensions_lib"]
        }
      ]
    }
  }
}
```

- `name` joins the canonical repository name back to the apparent/module name
  used as key in dependency metadata (eg `deps.yaml`).
- `reached_by` lists every root whose transitive closure contains the
  repository, retaining per-root identity so a mismatch can name the
  offending extension. `production` is true when a path exists from the root
  that does not traverse any `testonly` target.
- `consumers` lists the exact targets with a direct edge into the repository,
  each tagged with its `testonly` attribute and the roots it is reachable from.
  Consumers in other external repositories (`repo` != "") allow untracked
  transitive repositories to be attributed back to the tracking dependency.
- `consumers[].attrs` names the rule attributes the edges arrive on. This is
  the attribute vocabulary `excluded_edges` matches against, so the value to
  exclude can be read straight off the output rather than inferred from the
  defining rule. For example, to find what pulls in a repository:

  ```console
  jq -r '.dependencies["<repo>"].consumers[]
         | "\\(.target)\\t\\(.attrs | join(","))"' dep-reachability.json
  ```

The aspect emits raw truth: no repository is filtered. Policy (ignore lists,
test-only exemptions, bucketing by surface/extension/contrib) belongs in the
consumer of the JSON.

Note on attribute coverage: the aspect uses `attr_aspects = ["*"]` so it
propagates along every attribute of every rule it visits, including
non-standard attributes on custom rules (e.g. `library` on
`v8_lib_no_pointer_compression`). Resolved toolchain dependencies are *not*
included because `toolchains_aspects` is not set, so `["*"]` alone does not
reach them. Implicit/private attributes (`_`-prefixed names) are visited by
Bazel but excluded from recorded edges and provider accumulation. Edges are
recorded over all public attributes, including ones that carry build-time-only
deps (e.g. `tools`-style attrs on custom rules); consumers that need to
distinguish build-time from runtime paths should apply that policy themselves.

Exclusion settings (`excluded_edges`, `excluded_patterns`) are transported via
Starlark build settings rather than `--features`, so they survive Bazel's exec
configuration transition. They therefore apply uniformly across target and exec
configurations: edges reached through `cfg = "exec"` attributes are excluded
just as reliably as edges in the target configuration.

Note on exclusion semantics: an excluded repository is neither recorded nor
descended into. Pruning descent means that repositories reachable *only through*
an excluded repository also disappear from the output, even if they do not
themselves match any exclusion pattern. This is a deliberate trade-off: it keeps
the walk bounded but means the output can depend on which repository sits first
on a path.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Private build settings used to transport excluded_edges and excluded_patterns
# through the configuration transition. Build settings survive the exec
# configuration transition (unlike --features, which Bazel resets to
# --host_features when entering exec config). These settings are not intended
# for direct use; they are an implementation detail of dependency_reachability.
_EXCLUDED_EDGES_SETTING = "//dependency:_excluded_edges"
_EXCLUDED_PATTERNS_SETTING = "//dependency:_excluded_patterns"

DependencyReachabilityInfo = provider(
    doc = "Cross-repository dependency edges in a target's transitive closure.",
    fields = {
        "edges": "depset of edge structs for all reachable cross-repo edges",
        "production_edges": (
            "depset of edge structs reachable without traversing any " +
            "testonly target"
        ),
    },
)

def apparent_name(repo_name):
    """Best-effort apparent/module name for a canonical repository name.

    Handles bzlmod canonical forms - `module+` / `module~` for module repos
    and `module++ext+repo` / `module~~ext~repo` for extension-generated
    repos - as well as plain WORKSPACE repository names.
    """
    segments = [
        segment
        for segment in repo_name.replace("~", "+").split("+")
        if segment
    ]
    if not segments:
        return repo_name
    return segments[-1]

def _label_string(label):
    if not label.repo_name:
        return "//%s:%s" % (label.package, label.name)
    return str(label)

def _attr_targets(rule_attr, name):
    value = getattr(rule_attr, name, None)
    if value == None:
        return []
    if type(value) == "Target":
        return [value]
    if type(value) == "list":
        return [item for item in value if type(item) == "Target"]
    return []

def _matches_repo_pattern(repo_name, pattern):
    if pattern.endswith("*"):
        return repo_name.startswith(pattern[:-1])
    return repo_name == pattern

def _repo_is_excluded(repo_name, patterns):
    """Return True if repo_name matches any exclusion pattern.

    An excluded repository is neither recorded as a dependency edge nor
    descended into during traversal. Pruning descent means that repositories
    reachable *only through* an excluded repository also disappear from the
    output, even if they do not themselves match any exclusion pattern.
    """
    for pattern in patterns:
        if _matches_repo_pattern(repo_name, pattern):
            return True
    return False

def _reachability_transition_impl(settings, attr):
    return {
        _EXCLUDED_EDGES_SETTING: attr.excluded_edges,
        _EXCLUDED_PATTERNS_SETTING: attr.excluded_patterns,
    }

_reachability_transition = transition(
    implementation = _reachability_transition_impl,
    inputs = [],
    outputs = [
        _EXCLUDED_EDGES_SETTING,
        _EXCLUDED_PATTERNS_SETTING,
    ],
)

def _reachability_aspect_impl(target, ctx):
    consumer = _label_string(target.label)
    consumer_repo = target.label.repo_name
    testonly = bool(getattr(ctx.rule.attr, "testonly", False))
    excluded_edges = {edge: True for edge in ctx.attr._excluded_edges[BuildSettingInfo].value}
    excluded_patterns = ctx.attr._excluded_patterns[BuildSettingInfo].value
    edges = []
    transitive = []
    transitive_production = []
    for attr_name in [a for a in dir(ctx.rule.attr) if not a.startswith("_")]:
        if attr_name in excluded_edges:
            continue
        for dep in _attr_targets(ctx.rule.attr, attr_name):
            dep_repo = dep.label.repo_name
            if dep_repo and _repo_is_excluded(dep_repo, excluded_patterns):
                continue
            if dep_repo and dep_repo != consumer_repo:
                edges.append(struct(
                    attr = attr_name,
                    consumer = consumer,
                    consumer_repo = consumer_repo,
                    name = apparent_name(dep_repo),
                    repo = dep_repo,
                    target = _label_string(dep.label),
                    testonly = testonly,
                ))
            if DependencyReachabilityInfo in dep:
                info = dep[DependencyReachabilityInfo]
                transitive.append(info.edges)
                transitive_production.append(info.production_edges)
    return [DependencyReachabilityInfo(
        edges = depset(edges, transitive = transitive),
        production_edges = (
            depset()
            if testonly
            else depset(edges, transitive = transitive_production)
        ),
    )]

reachability_aspect = aspect(
    implementation = _reachability_aspect_impl,
    attr_aspects = ["*"],
    attrs = {
        "_excluded_edges": attr.label(
            default = _EXCLUDED_EDGES_SETTING,
            providers = [BuildSettingInfo],
        ),
        "_excluded_patterns": attr.label(
            default = _EXCLUDED_PATTERNS_SETTING,
            providers = [BuildSettingInfo],
        ),
    },
    doc = (
        "Collects cross-repository dependency edges over all public " +
        "attributes, tracking whether each edge is reachable without " +
        "traversing a testonly target, and recording the attribute name " +
        "each edge arrives on. Implicit/private attributes " +
        "(_-prefixed) are skipped at recording time. Resolved toolchain " +
        "dependencies are not visited because toolchains_aspects is not set. " +
        "Exclusion settings are read from Starlark build settings " +
        "(_excluded_edges, _excluded_patterns) that survive the exec " +
        "configuration transition, so exclusions apply uniformly across " +
        "target and exec configurations."
    ),
)

def _dependency_reachability_impl(ctx):
    deps = {}
    for target in ctx.attr.roots:
        root = _label_string(target.label)
        info = target[DependencyReachabilityInfo]
        production = {edge: True for edge in info.production_edges.to_list()}
        for edge in info.edges.to_list():
            entry = deps.setdefault(edge.repo, dict(
                name = edge.name,
                reached_by = {},
                targets = {},
                consumers = {},
            ))
            entry["targets"][edge.target] = True
            reached = entry["reached_by"].setdefault(root, dict(
                production = False,
            ))
            if edge in production:
                reached["production"] = True
            consumer = entry["consumers"].setdefault(edge.consumer, dict(
                repo = edge.consumer_repo,
                testonly = edge.testonly,
                attrs = {},
                roots = {},
            ))
            consumer["attrs"][edge.attr] = True
            consumer["roots"][root] = True
    dependencies = {}
    for repo in sorted(deps.keys()):
        entry = deps[repo]
        reached_by = [
            dict(
                root = root,
                production = entry["reached_by"][root]["production"],
            )
            for root in sorted(entry["reached_by"].keys())
        ]
        dependencies[repo] = dict(
            name = entry["name"],
            production = any([
                reached["production"]
                for reached in reached_by
            ]),
            reached_by = reached_by,
            targets = sorted(entry["targets"].keys()),
            consumers = [
                dict(
                    target = consumer,
                    repo = entry["consumers"][consumer]["repo"],
                    testonly = entry["consumers"][consumer]["testonly"],
                    attrs = sorted(entry["consumers"][consumer]["attrs"].keys()),
                    roots = sorted(entry["consumers"][consumer]["roots"].keys()),
                )
                for consumer in sorted(entry["consumers"].keys())
            ],
        )
    output = ctx.actions.declare_file("%s.json" % ctx.label.name)
    ctx.actions.write(
        output = output,
        content = json.encode_indent(
            dict(dependencies = dependencies),
            indent = "  ",
        ) + "\n",
    )
    return [DefaultInfo(files = depset([output]))]

def dependency_reachability_rule():
    return rule(
        implementation = _dependency_reachability_impl,
        attrs = {
            "roots": attr.label_list(
                aspects = [reachability_aspect],
                allow_files = True,
                mandatory = True,
                cfg = _reachability_transition,
                doc = (
                    "Concrete root targets to analyze. Each entry must be a " +
                    "resolved label — Bazel target patterns such as " +
                    "`//source/extensions/...` are resolved at the command " +
                    "line / loading phase and CANNOT be used as rule attribute " +
                    "values (analysis phase requires resolved targets). To cover " +
                    "many targets under one root, pass a concrete umbrella " +
                    "target (eg a `filegroup` or existing aggregate) that " +
                    "depends on them. Per-consumer attribution still falls out " +
                    "of `consumers[].target` labels regardless of how coarse " +
                    "the root is."
                ),
            ),
            "excluded_edges": attr.string_list(
                default = [],
                doc = (
                    "Rule attribute names excluded from traversal. Any edge " +
                    "carried on these attributes is not recorded and not " +
                    "traversed. The attribute names available to match against " +
                    "are reported as `consumers[].attrs` in the emitted JSON."
                ),
            ),
            "excluded_patterns": attr.string_list(
                default = [],
                doc = (
                    "Canonical repository-name patterns excluded from " +
                    "traversal. Supported forms are exact matches (`repo_name`) " +
                    "and a single trailing `*` wildcard (`prefix*`) for prefix " +
                    "matching."
                ),
            ),
            "_allowlist_function_transition": attr.label(
                default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
            ),
        },
        doc = (
            "Writes a JSON reachability map describing, for every external " +
            "repository reachable from the given root targets, which targets " +
            "reach it and whether any non-testonly path exists. Root targets " +
            "must be concrete labels — Bazel target patterns like " +
            "`//source/extensions/...` cannot be used as rule attribute values."
        ),
    )

dependency_reachability = dependency_reachability_rule()
