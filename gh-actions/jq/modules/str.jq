def indent:
  split("\n")
  | map("  " + .)
  | join("\n")
  ;
