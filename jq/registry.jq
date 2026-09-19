def default_repo: $ENV.REGISTRY_REPO // "https://github.com/envoyproxy/bazel-registry";
def default_branch: $ENV.REGISTRY_BRANCH // "main";
def default_url_prefix: $ENV.REGISTRY_URL_PREFIX // "https://raw.githubusercontent.com/envoyproxy/bazel-registry/";

def registry_output_default:
  $ENV.REGISTRY_CHANGES_OUTPUT
  // (($ENV.ENVOY_BUILD_DIR // "/build") + "/registry-changes.json");

def unique_preserve:
  reduce .[] as $item ([]; if index($item) == null then . + [$item] else . end);

def capture_value($match; $name):
  $match.captures[] | select(.name == $name);

def attr_match($body; $attr):
  try (
    $body
    | match("(?s)\\b" + $attr + "\\s*=\\s*\"(?<value>[^\"]*)\"")
  ) catch null;

def module_name_attr($kind):
  if $kind == "bazel_dep" then "name" else "module_name" end;

def regex_escape:
  explode
  | map([.] | implode)
  | map(
      . as $char
      | if ["\\", "^", "$", ".", "|", "?", "*", "+", "(", ")", "[", "]", "{", "}"] | index($char) then
        "\\" + $char
      else
        $char
      end)
  | join("");

def registry_pattern($url_prefix):
  "(?m)^common --registry="
  + ($url_prefix | regex_escape)
  + "(?<hash>[0-9a-f]+)$";

def registry_path($url_prefix; $hash):
  "common --registry=\($url_prefix)\($hash)";

def bazelrc_hash:
  . as $input
  | reduce ($input.paths // [])[] as $path ({hash: null, error: null};
      if .error != null then
        .
      else
        (($input.files[$path] // "")
         | try capture(registry_pattern($input.url_prefix // default_url_prefix)) catch null) as $match
        | if $match == null then
            .error = "Failed to determine current registry hash from \($path)"
          elif .hash != null and .hash != $match.hash then
            .error = "Registry hash mismatch: \($path) has \($match.hash), expected \(.hash)"
          else
            .hash = $match.hash
          end
      end)
  | if .error != null then {error: .error} else {hash: .hash} end;

def module_pins:
  . as $input
  | [($input.paths // [])[] as $path
     | ($input.files[$path] // "") as $content
     | [($content | match("(?s)(?<kind>bazel_dep|single_version_override)\\((?<body>.*?)\\)"; "g"))
        | . as $call
        | ($call | capture_value(.; "kind").string) as $kind
        | ($call | capture_value(.; "body")) as $body_capture
        | $body_capture.string as $body
        | attr_match($body; module_name_attr($kind)) as $name_match
        | attr_match($body; "version") as $version_match
        | select($name_match != null and $version_match != null)
        | (capture_value($name_match; "value")) as $name_value
        | (capture_value($version_match; "value")) as $version_value
        | {
            name: $name_value.string,
            version: $version_value.string,
            file: $path,
            kind: $kind,
            version_start: ($body_capture.offset + $version_value.offset),
            version_end: ($body_capture.offset + $version_value.offset + $version_value.length),
          }][]];

def registry_objects:
  [(.pins // [])[]
   | "modules/\(.name)/metadata.json",
     "modules/\(.name)/\(.version)/MODULE.bazel"]
  | unique_preserve;

def normalize_date_token($token):
  if ($token | length) == 8 then $token else "20\($token)" end;

def newest_version:
  if length == 0 then
    {error: "no replacement versions available"}
  else
    ([.[]
      | {version: ., token: (try capture("-(?<token>\\d{8}|\\d{6})(?=[-.]|$)").token catch null)}
      | select(.token != null)
      | .token |= normalize_date_token(.)] as $dated
     | if ($dated | length) > 0 then
         {version: ($dated | max_by(.token).version)}
       else
         {version: .[-1]}
       end)
  end;

def module_groups($pins):
  reduce $pins[] as $pin ({};
    .[$pin.name] = ((.[$pin.name] // {name: $pin.name, versions: [], files: [], pins: []})
      | .versions += [$pin.version]
      | .versions |= unique_preserve
      | .files += [$pin.file]
      | .files |= unique_preserve
      | .pins += [$pin]));

def hosted_module($exists; $name):
  $exists["modules/\($name)/metadata.json"] // false;

def hosted_version($exists; $name; $version):
  $exists["modules/\($name)/\($version)/MODULE.bazel"] // false;

def module_change($module_info; $target):
  if ([($module_info.versions[]) == $target] | all) then
    {modules: [], edits: []}
  else
    {
      modules: [{
        name: $module_info.name,
        from: ($module_info.versions | join(", ")),
        to: $target,
        files: $module_info.files,
      }],
      edits: [($module_info.pins[] | select(.version != $target)
        | {
            file: .file,
            name: .name,
            from: .version,
            to: $target,
            start: .version_start,
            end: .version_end,
          })],
    }
  end;

def metadata_modules:
  . as $input
  | ($input.pins // [])
  | map(.name)
  | unique_preserve
  | map(select(hosted_module($input.exists; .)));

def plan:
  . as $input
  | (module_groups($input.pins // [])) as $grouped
  | reduce (($grouped | keys) | sort[]) as $name ({
      registry: {old: $input.old_hash, new: $input.new_hash},
      modules: [],
      edits: [],
      errors: [],
      seen_overrides: [],
    };
      ($grouped[$name]) as $module_info
      | ($input.overrides[$name] // null) as $override
      | (hosted_module($input.exists; $name)) as $hosted
      | if $override != null then
          .seen_overrides += [$name]
          | if ($hosted | not) then
              .errors += ["FAIL: --set \($name)=\($override): module is not served by registry \($input.new_hash)"]
            elif (hosted_version($input.exists; $name; $override) | not) then
              .errors += ["FAIL: --set \($name)=\($override): version not found in registry \($input.new_hash)"]
            else
              (module_change($module_info; $override)) as $change
              | .modules += $change.modules
              | .edits += $change.edits
            end
        elif ($hosted | not) then
          .
        elif ([($module_info.versions[] | hosted_version($input.exists; $name; .))] | all) then
          .
        else
          (($input.metadata[$name].versions // []) | newest_version) as $replacement
          | if $replacement.error != null then
              .errors += ["FAIL: \($name)@\($module_info.versions[0]) removed from registry and no replacement versions available"]
            else
              (module_change($module_info; $replacement.version)) as $change
              | .modules += $change.modules
              | .edits += $change.edits
            end
        end)
  | reduce (($input.overrides | keys_unsorted[]) // empty) as $name (.;
      if (.seen_overrides | index($name)) != null then
        .
      elif hosted_module($input.exists; $name) then
        .errors += ["FAIL: --set \($name)=\($input.overrides[$name]): module is not pinned in configured MODULE.bazel files"]
      else
        .errors += ["FAIL: --set \($name)=\($input.overrides[$name]): module is not served by registry \($input.new_hash)"]
      end)
  | del(.seen_overrides);

def apply_edits:
  . as $input
  | reduce (($input.edits // []) | sort_by(.file, .start) | reverse[]) as $edit ({};
      .[$edit.file] = (((if has($edit.file) then .[$edit.file] else $input.files[$edit.file] end)
        | .[:$edit.start] + $edit.to + .[$edit.end:])));

def apply_hash:
  . as $input
  | reduce ($input.paths // [])[] as $path ({};
      . + {
        ($path): (($input.files[$path] // "")
          | sub(
              registry_pattern($input.url_prefix // default_url_prefix);
              registry_path($input.url_prefix // default_url_prefix; $input.hash)))
      });

def render_report:
  "Registry: \(.registry.old) -> \(.registry.new)\n"
  + "Registry modules updated:\n"
  + (if (.modules | length) == 0 then
       "  (none)"
     else
       (.modules
        | map((.files | join(", ")) as $files | "  \(.name)  \(.from) -> \(.to)  (\($files))")
        | join("\n"))
     end);

def check:
  . as $input
  | if ($input.skip_check // false) then
      {
        ok: true,
        messages: ["WARNING: skipping registry check for \($input.hash)"],
        errors: [],
      }
    elif ($input.exists_commit | not) then
      {
        ok: false,
        messages: [],
        errors: ["FAIL: Registry commit \($input.hash) not found in \($input.repo)"],
      }
    elif ($input.is_ancestor | not) then
      {
        ok: false,
        messages: [],
        errors: ["FAIL: Registry commit \($input.hash) is not an ancestor of \($input.branch)"],
      }
    else
      {
        ok: true,
        messages: ["Registry commit \($input.hash) is an ancestor of \($input.branch)"],
        errors: [],
      }
      | if ($input.tags | length) > 0 then
          .messages += [($input.tags | join(" ")) as $tags | "Registry commit \($input.hash) is tagged: \($tags)"]
        elif ($input.version_txt | endswith("-dev")) then
          .messages += ["WARNING: registry commit \($input.hash) is not a tagged version (ok for \($input.version_txt))"]
        else
          .ok = false
          | .errors += ["FAIL: Registry commit \($input.hash) is not a tagged version, required for release \($input.version_txt)"]
        end
    end;

def ls_remote_hash:
  split("\n")
  | map(select(length > 0))
  | first // ""
  | split("\t")[0] // "";

def batch_check_exists:
  split("\n")
  | map(select(length > 0))
  | reduce .[] as $line ({};
      ($line | capture("^(?<path>.+) (?<status>missing|blob|tree|commit|tag)$")) as $match
      | . + {($match.path): ($match.status != "missing")});

def parse_set_entry($entry):
  ($entry | capture("^(?<name>[^=]+)=(?<version>.+)$")?) // null;

def parse_args:
  def add_error($cfg; $message):
    $cfg | .errors += ["FAIL: " + $message];
  def add_set($cfg; $entry):
    (parse_set_entry($entry)) as $parsed
    | if $parsed == null then
        add_error($cfg; "Invalid --set value \($entry | @json), expected name=version")
      else
        $cfg | .overrides[$parsed.name] = $parsed.version
      end;
  def loop($index; $cfg):
    if $index >= ($ARGS.positional | length) then
      $cfg
    else
      ($ARGS.positional[$index]) as $arg
      | if $arg == "--hash" then
          if ($index + 1) < ($ARGS.positional | length) then
            loop($index + 2; $cfg | .hash = $ARGS.positional[$index + 1])
          else
            add_error($cfg; "Missing value for --hash")
          end
        elif ($arg | startswith("--hash=")) then
          loop($index + 1; $cfg | .hash = ($arg | ltrimstr("--hash=")))
        elif $arg == "--repo" then
          if ($index + 1) < ($ARGS.positional | length) then
            loop($index + 2; $cfg | .repo = $ARGS.positional[$index + 1])
          else
            add_error($cfg; "Missing value for --repo")
          end
        elif ($arg | startswith("--repo=")) then
          loop($index + 1; $cfg | .repo = ($arg | ltrimstr("--repo=")))
        elif $arg == "--branch" then
          if ($index + 1) < ($ARGS.positional | length) then
            loop($index + 2; $cfg | .branch = $ARGS.positional[$index + 1])
          else
            add_error($cfg; "Missing value for --branch")
          end
        elif ($arg | startswith("--branch=")) then
          loop($index + 1; $cfg | .branch = ($arg | ltrimstr("--branch=")))
        elif $arg == "--skip-check" then
          loop($index + 1; $cfg | .skip_check = true)
        elif $arg == "--check-only" then
          loop($index + 1; $cfg | .check_only = true)
        elif $arg == "--set" then
          if ($index + 1) < ($ARGS.positional | length) then
            loop($index + 2; add_set($cfg; $ARGS.positional[$index + 1]))
          else
            add_error($cfg; "Missing value for --set")
          end
        elif ($arg | startswith("--set=")) then
          loop($index + 1; add_set($cfg; ($arg | ltrimstr("--set="))))
        elif $arg == "--output" then
          if ($index + 1) < ($ARGS.positional | length) then
            loop($index + 2; $cfg | .output = $ARGS.positional[$index + 1])
          else
            add_error($cfg; "Missing value for --output")
          end
        elif ($arg | startswith("--output=")) then
          loop($index + 1; $cfg | .output = ($arg | ltrimstr("--output=")))
        elif $arg == "--dry-run" then
          loop($index + 1; $cfg | .dry_run = true)
        else
          loop($index + 1; add_error($cfg; "Unknown argument \($arg)"))
        end
    end;
  loop(0; {
    hash: null,
    repo: default_repo,
    branch: default_branch,
    skip_check: false,
    check_only: false,
    overrides: {},
    output: registry_output_default,
    dry_run: false,
    errors: [],
  })
  | if .check_only and .skip_check then
      .errors += ["FAIL: --skip-check is invalid with --check-only"]
    else
      .
    end;
