def filters:
  to_entries
  | map("$__data\n| \(.value)\n| (. as $__result | $__output | .[\"\(.key)\"] = $__result) as $__output") as $filters
      | [". as $__data\n| {} as $__output"] + $filters
  | join("\n| ")
      | . + "\n| $__output"
;

def bytesize:
  .
  | if . >= 1099511627776 then "\(.  / 1099511627776 * 100 | round / 100)TB"
    elif . >= 1073741824 then "\(. / 1073741824 * 100 | round / 100)GB"
    elif . >= 1048576 then "\(.  / 1048576 * 100 | round / 100)MB"
    elif . >= 1024 then "\(. / 1024 * 100 | round / 100)KB"
    else "\(.)B"
    end
;
