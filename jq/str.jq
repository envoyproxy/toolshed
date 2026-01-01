def cleaned:
  gsub("\u001b\\[[0-9;]*[a-zA-Z]"; "")
;

def indent(width):
  split("\n")
  | map(" " * width + .)
  | join("\n")
;

def isempty:
  (. | type == "null") or (. == "") or (. == "\"\"") or (. == "''")
;

def matches(matching; excluding):
  split("\n") as $lines
  | $lines
  | map(. as $line
         | matching
         | with_entries(
               .key as $k
               | .value as $tests
               | if any($tests[]; . as $test | $line | cleaned | test($test)) then
                   if ((excluding // {})[$k] // []) | any(.[]; . as $ntest | $line | cleaned | test($ntest)) then
                     {key: $k, value: null}
                   else {key: $k, value: $line} end
                 else {key: $k, value: null} end)
         | select(any(.[]; . != null)))
  | reduce .[] as $item (
             {};
             reduce ($item | to_entries[]) as $entry (
                      .;
                      if $item[$entry.key] // false then
                        .[$entry.key] += [$item[$entry.key]]
                      else . end))
;

def matches(matching):
  matches(matching; null)
;

def trim:
  sub("^ +"; "")
  | sub(" +$"; "")
;
