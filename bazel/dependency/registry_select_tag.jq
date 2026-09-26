include "version";

split("\n")
| map(select(length > 0))
| map({tag: ., version: (sub("^v"; ""))})
| if length == 0 then
    ""
  else
    sort_by(.version | version_key)
    | last
    | .tag
  end
