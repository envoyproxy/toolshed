import "str" as str;

def collapse:
  if (.open  // false) then
    .open = "open=\"open\""
  else
    .open = ""
  end
  | "
<details \(.open)>
  <summary><b>\(.title)</b></summary>

\(.content | str::indent(2))

</details>
"
;

def action(name):
  if name == "failure" then
    ":x: \(.)"
  else
    ":heavy_check_mark: \(.)"
  end
;

def fence(name):
  "
```\(name)
\(.)
```
"
;

def blockquote:
  split("\n")
  | map("> " + .)
  | join("\n")
;

def table_headers:
  . as $headers
  | ("| " + (. | join(" | ")) + " |")
      + "\n"
      + ("| " + "--- | " * ($headers | length))
;


def table(filter; ifempty; cells; sanitize):
  . as $table
  | ($table.headers | table_headers) as $headers
  | $table.data
  | filter
  | if (. | length) == 0 then
      ifempty
    else
      .
    end
  | to_entries
  | map([.key, .value] as $row
         | map(. as $cell
                | {table: $table, row: $row, cell: $cell}
                | cells
                | sanitize))
  | map(join("|"))
  | join("\n") as $rows
  | "\($headers)
\($rows)
"
;
