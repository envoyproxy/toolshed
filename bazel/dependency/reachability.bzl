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

For multi-configuration analysis, construct a reachability rule whose transition
outputs are fixed up front, then pass a config matrix:

```starlark
load(
    "@envoy_toolshed//dependency:reachability.bzl",
    "dependency_reachability_macro",
    "dependency_reachability_rule",
)

# Resolve the flag label against *this* repository. A bare `//bazel:wasm_runtime`
# string would be resolved relative to the repo defining the transition - ie
# @envoy_toolshed - and fail with "no such package '@@envoy_toolshed//bazel'".
WASM_RUNTIME_FLAG = str(Label("//bazel:wasm_runtime"))

_envoy_dependency_reachability = dependency_reachability_rule(
    flags = [WASM_RUNTIME_FLAG],
)

envoy_dependency_reachability = dependency_reachability_macro(_envoy_dependency_reachability)

envoy_dependency_reachability(
    name = "dep-reachability",
    roots = ["//source/exe:envoy_main_common_with_core_extensions_lib"],
    configs = {
        "default": {},
        "wasmtime": {WASM_RUNTIME_FLAG: "wasmtime"},
        "wamr": {WASM_RUNTIME_FLAG: "wamr"},
    },
)
```

Note that `rule()` may only be called during `.bzl` initialization, so the
construction above cannot live in a `BUILD` file - put it in a `.bzl` and load
the resulting macro.

`flags` must be fixed at construction because transition `outputs` are static:
they cannot vary per target instantiation. Prefer Starlark build settings where
possible. Note: `--define` cannot be varied because Bazel does not support
Starlark transitions on it; use a build setting instead
(https://bazel.build/rules/config#user-defined-build-settings).

Building the target writes `<name>.json`:

```json
{
  "dependencies": {
    "<canonical repo name>": {
      "name": "<apparent/module name>",
      "production": true,
      "configs": ["default"],
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
      ],
      "attributed_packages": [
        {
          "package": "//source/extensions/filters/network/example",
          "production": true,
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
  For a repeated consumer label, `testonly` is the logical OR across all
  recorded edges for that consumer.
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

- `attributed_packages` is present only when `attribution_patterns` is
  non-empty. It lists the matching main-repo packages whose transitive closure
  reaches the external repository, even when the only direct cross-repo edge is
  inside a shared non-matching package. `production` is true when at least one
  non-testonly path exists from that package to the repository; otherwise the
  attribution is testonly-only. This keeps the output proportional to the
  number of matching packages rather than to every intra-repo edge. For
  example, to ask which extension packages consume a repository:

  ```console
  jq -r '.dependencies["<repo>"].attributed_packages[]
         | select(.production)
         | .package' dep-reachability.json
  ```

- `configs` lists the analyzed config names in which the repository is reached.
  Reachability data is only as complete as the declared matrix: if a dependency
  is reachable in no declared config, it is absent from the emitted JSON.

When a dependency is reached in multiple analyzed configs, data is merged by
union semantics: `targets`/`configs` are unioned, `consumers[*].roots` and
`consumers[*].attrs` are unioned, `attributed_packages[*].roots` are unioned,
and `production`/`reached_by[*].production`/`attributed_packages[*].production`
are merged with logical OR.

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
just as reliably as edges in the target configuration. The same transport is
used for `attribution_patterns`, so opted-in package attribution applies
uniformly across all analyzed configurations. All three settings are carried
through every branch of the split transition.

Note on exclusion semantics: an excluded repository is neither recorded nor
descended into. Pruning descent means that repositories reachable *only through*
an excluded repository also disappear from the output, even if they do not
themselves match any exclusion pattern. This is a deliberate trade-off: it keeps
the walk bounded but means the output can depend on which repository sits first
on a path. The same pruning applies to `attributed_packages`: excluded
repositories are not attributed, and packages are not attributed to repositories
reachable only through an excluded repository.

`attribution_patterns` is opt-in and defaults to empty. When left unset, the
emitted JSON is byte-identical to the historical output and no attribution sets
are propagated through the aspect. Opt in only when a consumer specifically
needs transitive main-repo package attribution.
"""

load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Private build settings used to transport excluded_edges and excluded_patterns
# through the configuration transition. Build settings survive the exec
# configuration transition (unlike --features, which Bazel resets to
# --host_features when entering exec config). These settings are not intended
# for direct use; they are an implementation detail of dependency_reachability.
_EXCLUDED_EDGES_SETTING = "//dependency:_excluded_edges"
_EXCLUDED_PATTERNS_SETTING = "//dependency:_excluded_patterns"
_ATTRIBUTION_PATTERNS_SETTING = "//dependency:_attribution_patterns"

DependencyReachabilityInfo = provider(
    doc = "Cross-repository dependency edges (and optional package attributions) in a target's transitive closure.",
    fields = {
        "edges": "depset of edge structs for all reachable cross-repo edges",
        "production_edges": (
            "depset of edge structs reachable without traversing any " +
            "testonly target"
        ),
        "repos": (
            "depset of reachable canonical repository names when package " +
            "attribution is enabled, else None"
        ),
        "production_repos": (
            "depset of reachable canonical repository names on at least one " +
            "non-testonly path when package attribution is enabled, else None"
        ),
        "attributed_packages": (
            "depset of struct(package=..., repo=...) pairs for matching " +
            "main-repo packages that transitively reach each repo, else None"
        ),
        "production_attributed_packages": (
            "depset of struct(package=..., repo=...) pairs for matching " +
            "main-repo packages with at least one non-testonly path to each repo, else None"
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

def _package_string(label):
    if label.package:
        return "//%s" % label.package
    return "//"

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

def _repo_or_apparent_is_excluded(repo_name, patterns):
    return _repo_is_excluded(repo_name, patterns) or _repo_is_excluded(apparent_name(repo_name), patterns)

def _matches_package_pattern(package, pattern):
    if pattern == "//...":
        return True
    if pattern.endswith("/..."):
        prefix = pattern[:-4]
        return package == prefix or package.startswith(prefix + "/")
    return package == pattern

def _package_matches_patterns(package, patterns):
    for pattern in patterns:
        if _matches_package_pattern(package, pattern):
            return True
    return False

# Exported for testing only; not part of the public API.
package_pattern_matches = _matches_package_pattern

def _decode_configs(configs_attr):
    configs = {}
    for config in sorted(configs_attr.keys()):
        values = {}
        for assignment in configs_attr[config]:
            if "=" not in assignment:
                fail("Invalid config assignment '{}' in config '{}' (expected '<flag_label>=<value>')".format(assignment, config))
            key, value = assignment.split("=", 1)
            values[key] = value
        configs[config] = values
    if not configs:
        return {"default": {}}
    return configs

def _is_flag_label(label):
    """Return True if a config key looks like a build setting label.

    Accepts the main-repo form (`//pkg:flag`) as well as the repo-qualified
    apparent (`@repo//pkg:flag`, `@//pkg:flag`) and canonical (`@@repo//pkg:flag`)
    forms. A consumer in another repository must resolve its own labels, eg
    `str(Label("//bazel:wasm_runtime"))`, because a bare `//` string would be
    resolved against the repository defining the transition rather than the
    consumer's - so the resolved, repo-qualified forms must be accepted here.
    """
    return label.startswith("//") or (label.startswith("@") and "//" in label)

# Exported for testing only; not part of the public API.
def config_validation_error(configs, flags):
    allowed = {flag: True for flag in flags}
    declared = sorted(flags)
    for config in sorted(configs.keys()):
        for label in sorted(configs[config].keys()):
            if _is_flag_label(label):
                if label not in allowed:
                    return "Config '{}' varies '{}' but it is not declared in flags. Declared flags: {}".format(
                        config,
                        label,
                        declared,
                    )
            else:
                return (
                    "Config '{}' varies '{}', but config keys must be build setting labels " +
                    "starting with '//', '@//' or '@@'. " +
                    "Bazel does not support Starlark transitions on --define; use a build setting instead " +
                    "(https://bazel.build/rules/config#user-defined-build-settings)."
                ).format(config, label)
    return None

def _validate_config_labels(configs, flags):
    error = config_validation_error(configs, flags)
    if error != None:
        fail(error)

def _reachability_aspect_impl(target, ctx):
    consumer = _label_string(target.label)
    consumer_repo = target.label.repo_name
    consumer_package = _package_string(target.label)
    testonly = bool(getattr(ctx.rule.attr, "testonly", False))
    excluded_edges = {edge: True for edge in ctx.attr._excluded_edges[BuildSettingInfo].value}
    excluded_patterns = ctx.attr._excluded_patterns[BuildSettingInfo].value
    attribution_patterns = ctx.attr._attribution_patterns[BuildSettingInfo].value
    collect_attributions = bool(attribution_patterns)
    edges = []
    transitive = []
    transitive_production = []
    reachable_repos = []
    reachable_repos_transitive = []
    production_reachable_repos = []
    production_reachable_repos_transitive = []

    # Flat lists of struct(package=..., repo=...) pairs accumulated at this node.
    # Transitive pairs from deps flow up as depsets without per-node flattening,
    # eliminating the dict-of-depsets allocation of the previous design.
    #
    # The .to_list() calls in the matching-package block below
    # are unavoidable with a pure bottom-up aspect. Attribution requires pairing
    # a matching package with *all* repos in its transitive closure, but in a
    # bottom-up traversal the package's ancestors have not yet been visited when
    # the node is processed, so there is no way to know which packages above a
    # given repo edge will eventually match. The only correct alternative would
    # require top-down information (e.g. a second pass), which is not available
    # in a single Bazel aspect. The cross-product-at-root approximation
    # (propagate matching_packages and repos as independent depsets, multiply at
    # the rule) is deliberately rejected: it would incorrectly attribute package
    # B to repo R1 whenever any other matching package A also reaches R1, even
    # if B has no path to R1. The per-node flatten is therefore kept, but its
    # cost is bounded: it fires only at nodes whose package matches
    # attribution_patterns, and only when attribution is enabled.
    attributed_pairs_direct = []
    attributed_pairs_transitive = []
    production_attributed_pairs_direct = []
    production_attributed_pairs_transitive = []
    for attr_name in [a for a in dir(ctx.rule.attr) if not a.startswith("_")]:
        if attr_name in excluded_edges:
            continue
        for dep in _attr_targets(ctx.rule.attr, attr_name):
            dep_repo = dep.label.repo_name
            if dep_repo and _repo_or_apparent_is_excluded(dep_repo, excluded_patterns):
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
                if collect_attributions:
                    reachable_repos.append(dep_repo)
                    if not testonly:
                        production_reachable_repos.append(dep_repo)
            if DependencyReachabilityInfo in dep:
                info = dep[DependencyReachabilityInfo]
                transitive.append(info.edges)
                transitive_production.append(info.production_edges)
                if collect_attributions:
                    if info.repos != None:
                        reachable_repos_transitive.append(info.repos)
                    if not testonly and info.production_repos != None:
                        production_reachable_repos_transitive.append(info.production_repos)
                    if info.attributed_packages != None:
                        attributed_pairs_transitive.append(info.attributed_packages)
                    if not testonly and info.production_attributed_packages != None:
                        production_attributed_pairs_transitive.append(info.production_attributed_packages)
    if collect_attributions and not consumer_repo and _package_matches_patterns(consumer_package, attribution_patterns):
        for repo in depset(
            direct = reachable_repos,
            transitive = reachable_repos_transitive,
        ).to_list():
            attributed_pairs_direct.append(struct(package = consumer_package, repo = repo))
        if not testonly:
            for repo in depset(
                direct = production_reachable_repos,
                transitive = production_reachable_repos_transitive,
            ).to_list():
                production_attributed_pairs_direct.append(struct(package = consumer_package, repo = repo))
    return [DependencyReachabilityInfo(
        edges = depset(edges, transitive = transitive),
        production_edges = (
            depset() if testonly else depset(edges, transitive = transitive_production)
        ),
        repos = (
            None if not collect_attributions else depset(
                direct = reachable_repos,
                transitive = reachable_repos_transitive,
            )
        ),
        production_repos = (
            None if not collect_attributions else (
                depset() if testonly else depset(
                    direct = production_reachable_repos,
                    transitive = production_reachable_repos_transitive,
                )
            )
        ),
        attributed_packages = (
            None if not collect_attributions else depset(
                direct = attributed_pairs_direct,
                transitive = attributed_pairs_transitive,
            )
        ),
        production_attributed_packages = (
            None if not collect_attributions else (
                depset() if testonly else depset(
                    direct = production_attributed_pairs_direct,
                    transitive = production_attributed_pairs_transitive,
                )
            )
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
        "_attribution_patterns": attr.label(
            default = _ATTRIBUTION_PATTERNS_SETTING,
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
        "Exclusion settings and optional attribution patterns are read from " +
        "Starlark build settings that survive the exec configuration " +
        "transition, so they apply uniformly across target and exec " +
        "configurations."
    ),
)

def _record_edge(deps, config, root, edge, production):
    entry = deps.setdefault(edge.repo, dict(
        name = edge.name,
        reached_by = {},
        targets = {},
        consumers = {},
        configs = {},
        attributed_packages = {},
    ))
    entry["configs"][config] = True
    entry["targets"][edge.target] = True
    reached = entry["reached_by"].setdefault(root, dict(
        production = False,
    ))
    if production:
        reached["production"] = True
    consumer = entry["consumers"].setdefault(edge.consumer, dict(
        repo = edge.consumer_repo,
        testonly = False,
        attrs = {},
        roots = {},
    ))
    consumer["testonly"] = consumer["testonly"] or edge.testonly
    consumer["attrs"][edge.attr] = True
    consumer["roots"][root] = True

def _record_attributed_package(deps, config, root, repo, package, production):
    entry = deps[repo]
    entry["configs"][config] = True
    attributed = entry["attributed_packages"].setdefault(package, dict(
        production = False,
        roots = {},
    ))
    if production:
        attributed["production"] = True
    attributed["roots"][root] = True

def _dependency_reachability_impl(ctx):
    deps = {}
    emit_attributed_packages = bool(ctx.attr.attribution_patterns)

    # Split transitions fan out each root once per config, so flattening
    # depsets here scales with the declared matrix size.
    for config in sorted(ctx.split_attr.roots.keys()):
        for target in ctx.split_attr.roots[config]:
            root = _label_string(target.label)
            info = target[DependencyReachabilityInfo]
            production = {edge: True for edge in info.production_edges.to_list()}
            for edge in info.edges.to_list():
                _record_edge(
                    deps,
                    config,
                    root,
                    edge,
                    production = edge in production,
                )
            if emit_attributed_packages:
                prod_pairs = {}
                for p in info.production_attributed_packages.to_list():
                    prod_pairs.setdefault(p.repo, {})[p.package] = True
                for pair in info.attributed_packages.to_list():
                    _record_attributed_package(
                        deps,
                        config,
                        root,
                        pair.repo,
                        pair.package,
                        production = pair.package in prod_pairs.get(pair.repo, {}),
                    )
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
            configs = sorted(entry["configs"].keys()),
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
        if emit_attributed_packages:
            dependencies[repo]["attributed_packages"] = [
                dict(
                    package = package,
                    production = entry["attributed_packages"][package]["production"],
                    roots = sorted(entry["attributed_packages"][package]["roots"].keys()),
                )
                for package in sorted(entry["attributed_packages"].keys())
            ]
    output = ctx.actions.declare_file("%s.json" % ctx.label.name)
    ctx.actions.write(
        output = output,
        content = json.encode_indent(
            dict(dependencies = dependencies),
            indent = "  ",
        ) + "\n",
    )
    return [DefaultInfo(files = depset([output]))]

def _dependency_reachability_transition(flags):
    def _impl(settings, attr):
        configs = _decode_configs(attr.configs)
        _validate_config_labels(configs, flags)
        transitioned = {}
        for config in sorted(configs.keys()):
            values = configs[config]
            output = {}
            for flag in flags:
                if flag not in settings:
                    fail(
                        (
                            "Config '{}' declares transition flag '{}' but it is absent from transition settings. " +
                            "Available transition settings keys: {}. " +
                            "When passing cross-repository flags, resolve labels with str(Label(\"//pkg:flag\")) " +
                            "so the key exactly matches Bazel's transition settings key."
                        ).format(
                            config,
                            flag,
                            sorted(settings.keys()),
                        ),
                    )
                output[flag] = values.get(flag, settings[flag])

            # Carry exclusion settings through every branch of the split so they
            # apply uniformly across all analyzed configurations.
            output[_EXCLUDED_EDGES_SETTING] = attr.excluded_edges
            output[_EXCLUDED_PATTERNS_SETTING] = attr.excluded_patterns
            output[_ATTRIBUTION_PATTERNS_SETTING] = attr.attribution_patterns
            transitioned[config] = output
        return transitioned

    flag_inputs = list(flags)
    transition_outputs = flag_inputs + [
        _EXCLUDED_EDGES_SETTING,
        _EXCLUDED_PATTERNS_SETTING,
        _ATTRIBUTION_PATTERNS_SETTING,
    ]
    return transition(
        implementation = _impl,
        inputs = flag_inputs,
        outputs = transition_outputs,
    )

def _dependency_reachability_rule(flags = []):
    """Construct the internal dependency_reachability rule.

    flags: list of build setting labels (string_flag/bool_flag/label_flag) that
        instantiated targets may vary. Fixed at construction because transition
        outputs must be static.
    """
    reachability_transition = _dependency_reachability_transition(flags)
    return rule(
        implementation = _dependency_reachability_impl,
        attrs = {
            "roots": attr.label_list(
                aspects = [reachability_aspect],
                allow_files = True,
                mandatory = True,
                cfg = reachability_transition,
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
            "configs": attr.string_list_dict(
                default = {"default": []},
                doc = (
                    "Configuration matrix keyed by config name. Each value is " +
                    "a list of '<flag_label>=<value>' assignments where each key " +
                    "must be a build setting label ('//pkg:flag', or the " +
                    "repo-qualified '@//pkg:flag' / '@@repo//pkg:flag' forms a " +
                    "cross-repo consumer gets from str(Label(...))). " +
                    "Use the dependency_reachability macro form to pass a " +
                    "dict of assignment maps."
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
                    "Repository-name patterns excluded from traversal. Patterns " +
                    "are matched against both the canonical repository name and " +
                    "the apparent/module name emitted in dependency metadata, " +
                    "so metadata-facing patterns work under both WORKSPACE and " +
                    "bzlmod. Supported forms are exact matches (`repo_name`) and " +
                    "a single trailing `*` wildcard (`prefix*`) for prefix matching."
                ),
            ),
            "attribution_patterns": attr.string_list(
                default = [],
                doc = (
                    "Optional main-repo package patterns to attribute " +
                    "transitively to each reachable external repository. " +
                    "Supported forms are exact package matches (`//pkg`) and " +
                    "recursive subtree matches (`//pkg/...`). When empty, " +
                    "attributed_packages is omitted and no attribution sets are " +
                    "propagated through the aspect."
                ),
            ),
            "_allowlist_function_transition": attr.label(
                default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
            ),
        },
        doc = (
            "Writes a JSON reachability map describing, for every external " +
            "repository reachable from the given root targets, which targets " +
            "reach it and whether any non-testonly path exists. Optionally, " +
            "matching main-repo packages can also be attributed transitively " +
            "via attribution_patterns. Root targets must be concrete labels — " +
            "Bazel target patterns like `//source/extensions/...` cannot be " +
            "used as rule attribute values."
        ),
    )

def _encode_configs(configs):
    if configs == None:
        return {"default": []}
    if type(configs) != "dict":
        fail("configs must be a dict of config-name -> dict(flag_label -> value)")
    if not configs:
        return {"default": []}
    encoded = {}
    for config in sorted(configs.keys()):
        assignments = configs[config]
        if type(assignments) != "dict":
            fail("configs['{}'] must be a dict(flag_label -> value)".format(config))
        encoded[config] = [
            "{}={}".format(key, assignments[key])
            for key in sorted(assignments.keys())
        ]
    return encoded

def dependency_reachability_macro(impl):
    def _macro(name, roots, configs = None, **kwargs):
        impl(
            name = name,
            roots = roots,
            configs = _encode_configs(configs),
            **kwargs
        )

    return _macro

def dependency_reachability_rule(flags = []):
    """Construct a dependency_reachability rule varying the given build settings.

    flags: list of build setting labels (string_flag/bool_flag/label_flag) that
        instantiated targets may vary. Fixed at construction because transition
        outputs must be static.

        Consumers in another repository must resolve their own labels, eg
        `str(Label("//bazel:wasm_runtime"))` - a bare `//` string is resolved
        against the repository defining the transition, not the caller's.
    """
    return _dependency_reachability_rule(flags)

_dependency_reachability = dependency_reachability_rule()

dependency_reachability = dependency_reachability_macro(_dependency_reachability)
