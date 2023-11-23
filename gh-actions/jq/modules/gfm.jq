import "str" as str;

def collapse(title):
  "
<details>
  <summary><b>\(title)</b></summary>

\(. | str::indent(2))

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
