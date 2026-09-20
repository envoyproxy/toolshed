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
         | try capture(registry_pattern($input.url_prefix)) catch null) as $match
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

def exists:
  if type == "array" then
    {pins: .[0], index: .[1]} | exists
  else
    . as $input
    | reduce ($input.pins // [])[] as $pin ({};
        ($input.index.modules[$pin.name] // null) as $entry
        | . + {
            ("modules/\($pin.name)/metadata.json"): ($entry != null),
            ("modules/\($pin.name)/\($pin.version)/MODULE.bazel"): (($entry.versions // []) | index($pin.version) != null),
          })
  end;

def overrides_from_flag:
  if type == "array" then
    {entries: .} | overrides_from_flag
  else
    reduce (.entries // . // [])[] as $entry ({overrides: {}, errors: []};
      (($entry | capture("^(?<name>[^=]+)=(?<version>.+)$")?) // null) as $parsed
      | if $parsed == null then
          .errors += ["FAIL: --set \($entry | @json): expected name=version"]
        else
          .overrides[$parsed.name] = $parsed.version
        end)
  end;

def plan:
  if type == "array" then
    {
      pins: .[0],
      exists: .[1],
      index: .[2],
      current: .[3],
      info: .[4],
      overrides: .[5],
    } | plan
  else
    . as $input
    | ($input.overrides.overrides // $input.overrides // {}) as $overrides
    | ($input.overrides.errors // []) as $override_errors
    | (module_groups($input.pins // [])) as $grouped
    | reduce (($grouped | keys) | sort[]) as $name ({
        registry: {old: $input.current.hash, new: $input.info.hash},
        modules: [],
        edits: [],
        errors: $override_errors,
        seen_overrides: [],
      };
        ($grouped[$name]) as $module_info
        | ($overrides[$name] // null) as $override
        | (hosted_module($input.exists; $name)) as $hosted
        | if $override != null then
            .seen_overrides += [$name]
            | if ($hosted | not) then
                .errors += ["FAIL: --set \($name)=\($override): module is not served by registry \($input.info.hash)"]
              elif (hosted_version($input.exists; $name; $override) | not) then
                .errors += ["FAIL: --set \($name)=\($override): version not found in registry \($input.info.hash)"]
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
            (($input.index.modules[$name].metadata.versions // $input.index.modules[$name].versions // []) | newest_version) as $replacement
            | if $replacement.error != null then
                .errors += ["FAIL: \($name)@\($module_info.versions[0]) removed from registry and no replacement versions available"]
              else
                (module_change($module_info; $replacement.version)) as $change
                | .modules += $change.modules
                | .edits += $change.edits
              end
          end)
    | reduce (($overrides | keys_unsorted[]) // empty) as $name (.;
        if (.seen_overrides | index($name)) != null then
          .
        elif hosted_module($input.exists; $name) then
          .errors += ["FAIL: --set \($name)=\($overrides[$name]): module is not pinned in configured MODULE.bazel files"]
        else
          .errors += ["FAIL: --set \($name)=\($overrides[$name]): module is not served by registry \($input.info.hash)"]
        end)
    | del(.seen_overrides)
  end;

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
              registry_pattern($input.url_prefix);
              registry_path($input.url_prefix; $input.hash)))
      });

def apply:
  if type == "array" then
    {
      plan: .[0],
      current: .[1],
      bazelrc_files: .[2],
      module_files: .[3],
      url_prefix: $ARGS.named.url_prefix,
    } | apply
  else
    . as $input
    | if (($input.plan.errors // []) | length) > 0 then
        []
      else
        (if $input.plan.registry.old != $input.plan.registry.new then
           ({files: $input.bazelrc_files, paths: ($input.bazelrc_files | keys_unsorted), url_prefix: $input.url_prefix, hash: $input.plan.registry.new}
            | apply_hash
            | to_entries
            | map({path: .key, content: .value}))
         else
           []
         end) as $hash_edits
        | ({files: $input.module_files, edits: ($input.plan.edits // [])}
           | apply_edits
           | to_entries
           | map({path: .key, content: .value})) as $module_edits
        | $hash_edits + $module_edits
      end
  end;

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
  if type == "array" then
    (.[3] // false) as $check_only
    | {
        hash: (if $check_only then .[0].hash else .[1].hash end),
        version_txt: .[2].version,
        branch: ($ARGS.named.branch // .[1].branch),
        repo: ($ARGS.named.repo // .[1].repo),
        tags: (.[1].tags // []),
        commit_exists: (.[1].commit_exists // false),
        is_ancestor: (.[1].is_ancestor // false),
        skip_check: (.[1].skip_check // false),
      } | check
  else
    . as $input
    | if ($input.skip_check // false) then
        {
          ok: true,
          messages: ["WARNING: skipping registry check for \($input.hash)"],
          errors: [],
        }
      elif ($input.commit_exists | not) then
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
      end
  end;
