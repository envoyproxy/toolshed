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

def version:
  . as $input
  | endswith("-dev") as $is_dev
  | ($input | split("-") | .[0]) as $base
  | ($base
     | capture("^(?<maj>[0-9]+)\\.(?<min>[0-9]+)\\.(?<pat>[0-9]+)(\\.post(?<post>[0-9]+))?$")
       // error("utils::version: unsupported version string: \($input)")) as $match
  | ($match.maj | tonumber) as $major
  | ($match.min | tonumber) as $minor
  | ($match.pat | tonumber) as $patch
  | ($match.post | if . == null then null else tonumber end) as $post
  | (if $is_dev then $base
     elif $post != null then "\($major).\($minor).\($patch).post\($post + 1)-dev"
     else "\($major).\($minor).\($patch + 1)-dev"
     end) as $next
  | {
      version: $input,
      is_dev:  $is_dev,
      major: $major,
      minor:  $minor,
      patch: $patch,
      post: $post,
      next: $next
    }
;
