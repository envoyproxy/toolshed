def indent(width):
  split("\n")
  | map(" " * width + .)
  | join("\n")
;

def trim:
  sub("^ +"; "")
  | sub(" +$"; "")
;
