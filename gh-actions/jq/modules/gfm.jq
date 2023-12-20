import "str" as str;
import "utils" as utils;

def action(name):
  if name == "failure" then
    ":x: \(.)"
  else
    ":heavy_check_mark: \(.)"
  end
;

def blockquote:
  split("\n")
  | map("> " + .)
  | join("\n")
;

def collapse:
  if (.open  // false) then
    .open = "open=\"open\""
  else
    .open = ""
  end
  | if (.indent | type == "null") then
      .indent = 2
    else . end
  | .indent as $indent
  | "
<details \(.open)>
  <summary><b>\(.title)</b></summary>

\(.content | str::indent($indent))

</details>
"
;

def event_title:
  .
  | .event as $event
  | .link as $link
  | .sha as $sha
  | .repo as $repo
  | .title as $title
  | .["target-branch"] as $targetBranch
  | .pr as $pr
  | {}
  | if $title != "" then
      .link = $title
    elif $link != "" then
      if $event != "" then
        .link = $event
      elif $pr != "" then
        .link = "pr/\($pr)"
      else
        .link = "postsubmit"
      end
      | .link |= "\(.)/\($targetBranch)@\($sha[:7])"
    else
      if $event != "" then
        .link = $event
      elif $pr != "" then
        .link = "pr/[\($pr)](https://github.com/\($repo)/pull/\($pr))"
      else
        .link = "postsubmit"
      end
      | "[\($sha[:7])](https://github.com/\($repo)/commit/\($sha))" as $shaLink
      | .link |= "\(.)/\($targetBranch)@\($shaLink)"
    end
 | .link
;

def fence(name):
  "
```\(name)
\(.)
```
"
;

def table_headers:
  . as $headers
  | ("| " + (. | join(" | ")) + " |")
      + "\n"
      + ("| " + "--- | " * ($headers | length))
;

def table_cell_sanitize:
  .cell as $cell
  | .row as $row
  | $cell
  | if type == "null" then
      ""
    elif (type == "boolean" or type == "number") then
      "`\(.)`"
    elif (type == "string" and test("\n")) then
      (split("\n")[0] + "..." )
    else . end
  | tojson
  | gsub("\\\\\\("; "\\\\\\(")
  | gsub("\\$"; "<span>$</span>")
  | .[1:-1]
;

def table(filter; ifempty; mutate; sanitize):
  . as $table
  | ($table.headers // [] | table_headers) as $headers
  | $table.data
  | (filter // .)
  | if (. | length) == 0 then
      ifempty // .
    else
      .
    end
  | to_entries
  | map([.key, .value] as $row
         | map(. as $cell
                | {table: $table, row: $row, cell: $cell}
                | (mutate // .cell) as $cell
                | {table: $table, row: $row, cell: $cell}
                | (sanitize // table_cell_sanitize)))
  | map(join("|"))
  | join("\n") as $rows
  | "\($headers)
\($rows)
"
;

def tables(mutate):
  to_entries
  | map(
      .key as $k
      | .value as $v
      | {data: $v.data,
         collapse: $v.collapse,
         title: $v.title,
         "collapse-open": $v["collapse-open"],
         "table-title": $v["table-title"],
         headers: ($v.headers // ["Key", "Value"])}
      | table(null; null; mutate // .cell; null) as $t
      | ($v.heading // "") as $heading
      | $v["table-title"] as $summary
      | $v.title as $title
      | if $v.collapse then
          $title as $_title
          | $summary as $title
          | "
#### \($title)

\($t)
"
          | {title: $_title, content: ., open: $v["collapse-open"] }
          | collapse
        else
          "
#### \($title)

\($t)
"
        end
        | . as $content
        | if $heading != "" then
            "
## \($heading)

\($content)
"
          else . end)
      | join("\n")
;

def tables:
  tables(null)
;
