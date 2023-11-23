def indent(width):
  split("\n")
  | map(" " * width + .)
  | join("\n")
  ;
