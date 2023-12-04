def filters:
  to_entries
  | map("$__data\n| \(.value)\n| (. as $__result | $__output | .[\"\(.key)\"] = $__result) as $__output") as $filters
      | [". as $__data\n| {} as $__output"] + $filters
  | join("\n| ")
      | . + "\n| $__output"
;
