def indent(width):
  split("\n")
  | map(" " * width + .)
  | join("\n")
;

def trim:
  sub("^ +"; "")
  | sub(" +$"; "")
;

def isempty:
  (. | type == "null") or (. == "") or (. == "\"\"") or (. == "''")
;
