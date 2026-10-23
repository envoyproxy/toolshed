# Coverage reports for grcov covdir JSON. Configuration is an object (or null),
# and source directories are an array of paths, not a newline-delimited string.

def round_to_precision($precision):
  . * pow(10; $precision) | round / pow(10; $precision);

def get_default_threshold($config):
  $config.thresholds.per_directory // 0;

def calculate_summary($config):
  ($config.thresholds.total // 0) as $threshold
  | {
      coverage_percent: (.coveragePercent | round_to_precision(1)),
      lines_covered: .linesCovered,
      lines_total: .linesTotal,
      threshold: $threshold,
      threshold_reached: (.coveragePercent >= $threshold)
    };

def directory_stats($config; $path):
  {
    expected_percent: ($config.directories[$path] // get_default_threshold($config)),
    coverage_percent: (.coveragePercent | round_to_precision(1)),
    lines_covered: .linesCovered,
    lines_total: .linesTotal
  };

def extract_dirs($config; $path):
  if .children then
    (if $path != "" and .coveragePercent != null and .linesCovered != null and .linesTotal != null then
       {($path): directory_stats($config; $path)}
     else empty end),
    (.children
     | to_entries[]
     | .key as $name
     | .value
     | extract_dirs($config; if $path == "" then $name else $path + "/" + $name end))
  else empty end;

def categorize_directories($config; $source_directories):
  . as $coverage_data
  | get_default_threshold($config) as $default
  | reduce $source_directories[] as $dir
      ({failed_coverage: [], low_coverage: [], excellent_coverage: [], high_coverage_adjustable: []};
       ($coverage_data[$dir] // null) as $dir_data
       | if $dir_data then
           $dir_data.expected_percent as $threshold
           | $dir_data.coverage_percent as $coverage
           | {directory: $dir, coverage_percent: $coverage, threshold: $threshold} as $entry
           | if $coverage < $threshold then
               .failed_coverage += [$entry]
             elif $threshold < $default then
               .low_coverage += [$entry]
               | if $coverage > $threshold then
                   .high_coverage_adjustable += [$entry]
                 else . end
             elif $coverage >= $default then
               .excellent_coverage += [$entry | del(.threshold)]
             else . end
         else . end);

def should_process_directories($config; $source_directories):
  $config != null
  and (($source_directories | length) > 0 or ($config.directories // {} | length) > 0);

def generate_summary_message:
  if .summary.threshold_reached then
    "Code coverage \(.summary.coverage_percent)% is good and higher than limit of \(.summary.threshold)%"
  else
    "Code coverage \(.summary.coverage_percent)% is lower than limit of \(.summary.threshold)%"
  end;

def generate_summary_failed:
  (if (.validation.failed_coverage | length) > 0 then
     ["FAILED: Directories not meeting coverage thresholds:"]
     + (.validation.failed_coverage
        | map("  ✗ \(.directory): \(.coverage_percent)% (threshold: \(.threshold)%)"))
     + [""]
   else [] end)
  | join("\n");

def generate_summary_adjustable:
  (if (.validation.high_coverage_adjustable | length) > 0 then
     ["WARNING: Coverage in the following directories may be adjusted up:"]
     + (.validation.high_coverage_adjustable
        | map("  ⬆  \(.directory): \(.coverage_percent)% (current threshold: \(.threshold)%)"))
     + [""]
   else [] end)
  | join("\n");

def generate_summary_excellent:
  (if (.validation.excellent_coverage | length) > 0 then
     ["Directories with excellent coverage (>= \(.default_threshold)%):"]
     + (.validation.excellent_coverage
        | map("  ✓ \(.directory): \(.coverage_percent)%"))
     + [""]
   else [] end)
  | join("\n");

def generate_summary_low:
  (if (.validation.low_coverage | length) > 0 then
     ["Directories with known low coverage (meeting configured thresholds):"]
     + (.validation.low_coverage
        | map("  ⚠ \(.directory): \(.coverage_percent)% (configured threshold: \(.threshold)%)"))
     + [""]
   else [] end)
  | join("\n");

def generate_summary_adjust_message:
  if .validation_summary.adjustable_count > 0 then
    "Can be adjusted up: \(.validation_summary.adjustable_count)"
  else "" end;

def generate_summary_directory_error:
  if (.validation_summary.all_passed | not) then
    "ERROR: Coverage check failed. Some directories are below their thresholds."
  else "" end;

def generate_summary_report:
  "
================== Per-Directory Coverage Report ==================

\(generate_summary_excellent)
\(generate_summary_low)
\(generate_summary_adjustable)
\(generate_summary_failed)
==================================================================
Overall Coverage: \(.summary.coverage_percent)%
Source directories checked: \(.validation_summary.total_directories),
Failed: \(.validation_summary.failed_count),
Low coverage (configured): \(.validation_summary.low_coverage_count),
Excellent coverage: \(.validation_summary.excellent_coverage_count)
\(generate_summary_adjust_message)
==================================================================

\(generate_summary_message)
\(generate_summary_directory_error)
";

def report($config; $source_directories):
  {
    summary: calculate_summary($config),
    source_directories: $source_directories,
    per_directory_coverage: (
      if should_process_directories($config; $source_directories) then
        [(.children // {})
         | to_entries[]
         | .key as $root_dir
         | .value
         | extract_dirs($config; $root_dir)]
        | add // {}
      else {} end),
    default_threshold: get_default_threshold($config),
    coverage_config: $config
  }
  | if should_process_directories($config; $source_directories) and $source_directories != [] then
      (.per_directory_coverage | categorize_directories($config; $source_directories)) as $validation
      | . + {
          validation: $validation,
          validation_summary: ($validation | {
            total_directories: ((.failed_coverage + .low_coverage + .excellent_coverage)
                                | map(.directory) | unique | length),
            failed_count: (.failed_coverage | length),
            low_coverage_count: (.low_coverage | length),
            excellent_coverage_count: (.excellent_coverage | length),
            adjustable_count: (.high_coverage_adjustable | length),
            all_passed: ((.failed_coverage | length) == 0)
          })
        }
    else . end
  | . + {summary_message: generate_summary_message}
  | if .validation then . + {summary_report: generate_summary_report} else . end;
