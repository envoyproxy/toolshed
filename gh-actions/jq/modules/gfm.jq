def collapse(title):
  "
  <details>
    <summary><b>\(title)</b></summary>

    \(.)

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
