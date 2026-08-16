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

def b64_to_hex:
  def b64chars:
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
  ;
  def b64val($c):
    if $c == "=" then
      null
    else
      b64chars
      | explode
      | index(($c | explode[0]))
    end
  ;
  def bytes_to_hex:
    map("0123456789abcdef"[(. / 16 | floor):(. / 16 | floor) + 1]
        + "0123456789abcdef"[. % 16:. % 16 + 1])
    | add
  ;
  explode
  | map([.] | implode)
  | [range(0; length; 4) as $i | .[$i:$i + 4]]
  | map(
      map(b64val(.)) as $q
      | [($q[0] * 4 + ($q[1] / 16 | floor))]
        + (if $q[2] != null then
             [((($q[1] % 16) * 16) + ($q[2] / 4 | floor))]
           else [] end)
        + (if $q[3] != null then
             [((($q[2] % 4) * 64) + $q[3])]
           else [] end))
  | add
  | bytes_to_hex
;

def integrity_to_hex:
  ltrimstr("sha256-") | b64_to_hex
;
