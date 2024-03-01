import "bash" as bash;
import "str" as str;

def log_bubble(matching; excluding):
  str::matches(matching; excluding)
  | . as $bubble
  | $bubble.notice // []
  | unique
  | if length > 10 then
      .[:9] + ["... and \(.|length - 9) more notices"]
    else . end
  | map("echo ::notice::\(.)") as $notices
  | $bubble.error // []
  | unique
  | if length > 10 then
      .[:9] + ["... and \(.|length - 9) more errors"]
    else . end
  | map("echo ::error::\(.)") as $errors
  | $bubble.warning // []
  | unique
  | if length > 10 then
      .[:9] + ["... and \(.|length - 9) more warnings"]
    else . end
  | map("echo ::warning::\(.)") as $warnings
  | $bubble.fail // []
  | if length > 0 then
      join("\n  ")
      | ["echo ::error::Failure: \n  \(.)", "exit 1"]
    else . end
  | . as $exit
  | ($notices + $errors + $warnings + $exit)
  | bash::xfor
;

def log_bubble(matching):
  log_bubble(matching; null)
;
