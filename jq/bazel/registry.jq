import "bazel/version" as version;

def regex_escape:
  explode
  | map([.] | implode)
  | map(if test("[][(){}.^$*+?|\\\\-]") then "\\" + . else . end)
  | join("");

def glob_to_regex($glob):
  "^"
  + (($glob | explode | map(
        if . == 42 then ".*"
        elif . == 63 then "."
        else ([.] | implode | regex_escape)
        end
      )) | join(""))
  + "$";

def normalize_sha:
  ascii_downcase
  | if test("^[0-9a-f]{40}$") then
      .
    else
      error("registry SHA must be a full 40-character hex commit")
    end;

def ls_remote_head:
  split("\n")
  | map(select(length > 0) | capture("^(?<sha>[0-9a-fA-F]{40})\\t"))
  | .[0].sha
  | normalize_sha;

def bazelrc_pin($url):
  ($url | regex_escape) as $prefix_re
  | [split("\n")[]
     | select(test("^[A-Za-z0-9_:-]* --registry=" + $prefix_re + "/[0-9A-Fa-f]{40}[[:space:]]*$"))
     | sub("^[A-Za-z0-9_:-]* --registry=" + $prefix_re + "/"; "")
     | sub("[[:space:]]*$"; "")
     | normalize_sha] as $matches
  | ($matches | unique) as $distinct
  | if ($distinct | length) == 0 then
      error("No '--registry=\($url)/<sha>' line found")
    elif ($distinct | length) != 1 then
      error("Found multiple differing '--registry=\($url)/<sha>' pins")
    else
      $distinct[0]
    end;

def ls_remote_tags:
  reduce (split("\n")[] | select(length > 0) | capture("^(?<sha>[0-9a-fA-F]{40})\\trefs/tags/(?<tag>.+)$")) as $line
    ({};
     ($line.tag | sub("\\^\\{\\}$"; "")) as $tag
     | .[$tag] = if ($line.tag | endswith("^{}")) or (.[$tag] == null) then ($line.sha | normalize_sha) else .[$tag] end);

def select_release($glob):
  (glob_to_regex($glob)) as $pattern
  | [to_entries[]
     | select(.key | test($pattern))
     | {tag: .key, version: (.key | sub("^v"; ""))}]
  | if length == 0 then
      error("No registry tag matches \($glob)")
    else
      sort_by(.version | version::version_key)
      | last
      | .tag
    end;

def tags_for($sha):
  ($sha | normalize_sha) as $target
  | [to_entries[] | select((.value | normalize_sha) == $target) | .key];

def resolve_output($sha; $url; $branch; $latest; $requested; $ancestor; $tags; $unsafe):
  {
    sha: $sha,
    url: ($url + "/" + $sha),
    branch: $branch,
    latest: $latest,
    ancestor: $ancestor,
    tags: $tags,
    requested: $requested,
    unsafe: $unsafe,
  };

def check_output($sha; $ancestor; $tags; $latest; $behind):
  {
    sha: $sha,
    ancestor: $ancestor,
    tags: $tags,
    latest: $latest,
    behind: $behind,
  };

def bazelrc_pin_from_args: bazelrc_pin($ARGS.named.url);
def select_release_from_args: select_release($ARGS.named.glob);
def select_release_sha_from_args: . as $tags | ($tags | select_release($ARGS.named.glob)) as $tag | ($tags[$tag] | normalize_sha);
def tags_for_from_args: tags_for($ARGS.named.sha);
def resolve_output_from_args: resolve_output($ARGS.named.sha; $ARGS.named.url; $ARGS.named.branch; $ARGS.named.latest; $ARGS.named.requested; $ARGS.named.ancestor; $ARGS.named.tags; $ARGS.named.unsafe);
def check_output_from_args: check_output($ARGS.named.sha; $ARGS.named.ancestor; $ARGS.named.tags; $ARGS.named.latest; $ARGS.named.behind);
