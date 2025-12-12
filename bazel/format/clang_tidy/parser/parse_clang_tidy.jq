#!/usr/bin/env jq -Rrf
# Parse clang-tidy stdout output to JSON
#
# This script parses raw clang-tidy output (from a single invocation) into
# structured JSON format for further processing and aggregation.
#
# Input: clang-tidy stdout (raw text, one line at a time via -R flag)
# Output: JSON array of diagnostic objects
#
# Each diagnostic object contains:
#   - file: source file path
#   - line: line number
#   - column: column number
#   - severity: "error", "warning", "note", etc.
#   - message: diagnostic message text
#   - check: check name (e.g., "modernize-use-auto")
#   - context_lines: array of context/code snippet lines
#
# Usage:
#   clang-tidy <args> | jq -Rf parse_clang_tidy.jq
#   cat clang_tidy_output.txt | jq -Rf parse_clang_tidy.jq

# Collect all input lines into an array (including the first line)
[., inputs] | 

# Join lines back together for processing
join("\n") |

# Split on lines that match the diagnostic pattern (file:line:col: severity:)
# This regex matches: <filepath>:<line>:<col>: <severity>: <message>
split("\n") |

# Process lines to build diagnostic entries
reduce .[] as $line (
  {diagnostics: [], current: null, context: []};
  
  # Check if this line starts a new diagnostic
  if ($line | test("^[^:]+:[0-9]+:[0-9]+: (error|warning|note|remark|fatal error): ")) then
    # Parse the diagnostic line
    (($line | match("^([^:]+):([0-9]+):([0-9]+): (error|warning|note|remark|fatal error): (.*)$")) as $m |
      # Save previous diagnostic if exists
      (if .current then
        .diagnostics += [.current + {context_lines: .context}]
      else . end) |
      # Extract message and check name from the message line
      ($m.captures[4].string | 
        if test("\\[([^\\]]+)\\]\\s*$") then
          match("^(.*)\\s*\\[([^\\]]+)\\]\\s*$") | 
          {msg: (.captures[0].string | sub("^\\s+"; "") | sub("\\s+$"; "")), chk: .captures[1].string}
        else
          {msg: (. | sub("^\\s+"; "") | sub("\\s+$"; "")), chk: ""}
        end
      ) as $parsed |
      # Start new diagnostic
      .current = {
        file: $m.captures[0].string,
        line: ($m.captures[1].string | tonumber),
        column: ($m.captures[2].string | tonumber),
        severity: $m.captures[3].string,
        message: $parsed.msg,
        check: $parsed.chk,
        context_lines: []
      } |
      .context = []
    )
  # Check if this is a summary line to ignore
  elif ($line | test("^[0-9]+ (warning|error|note)s? (and [0-9]+ (warning|error|note)s? )?generated\\.\\s*$")) then
    .
  # Check if this is an empty line
  elif ($line | test("^\\s*$")) then
    .
  # Otherwise, it's context for the current diagnostic
  elif .current then
    .context += [$line]
  else
    .
  end
) |

# Add the last diagnostic if exists
(if .current then
  .diagnostics += [.current + {context_lines: .context}]
else . end) |

# Return the array of diagnostics
.diagnostics
