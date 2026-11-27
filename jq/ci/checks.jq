# Pass rates of CI from the checks on a branch's commits, and reports of them.
#
# The stages are separate so that the one which talks to GitHub can stay small:
#
#   fetched commits and checks -> runs      which workflow runs to fetch the jobs of
#   fetched commits, checks and jobs -> report
#   reports of the months of a year -> year
#   report -> summary (GFM), slack (a `chat.postMessage` payload)
#
# The fetched data, a "raw" report, is the frame of the report and what GitHub
# returned, unprocessed:
#
#   {schema, repo, period, frame, complete, generated, since, until,
#    branches: {<branch>: [{sha, date, title,
#                           checks: [{name, status, conclusion, run_id, text}]}]},
#    jobs: {<run id>: [{name, conclusion}]}}
#
# `status` and `conclusion` are as the GraphQL API gives them for a check run
# (`COMPLETED`, `SUCCESS`), and a job's `conclusion` as the REST API does
# (`failure`). `period` is `week`, `month` or `year`, and the times are
# `%Y-%m-%dT%H:%M:%SZ`.

def SCHEMA: 6;

def OUTCOMES: ["success", "failure", "cancelled", "pending", "other"];

# The finishing job fails whenever anything else did.
def FINISH_JOB: "request / complete";

# The check names the calling job (`build-openssl`), and the run has that job's
# own jobs (`Check / OpenSSL (test) / ...`), so they are matched on what is
# left without these.
def GENERIC_WORDS: ["build", "check", "checks", "test", "tests"];

def TOP_JOBS: 20;
def CHART_JOBS: 15;
def TREND_JOBS: 10;

def CELLS: {success: "🟩", failure: "🟥", cancelled: "⬛", pending: "🟨", other: "🟨"};
def NO_CHECK: "⬜";

# Lowest pass rate for each colour: full green, darker green, orange, then red.
def RATE_COLOURS: [[100, "#2da44e"], [90, "#116329"], [80, "#bc4c00"], [0, "#cf222e"]];

# The same scale as cells, which have no darker green.
def RATE_CELLS: [[100, "🟩"], [90, "🟨"], [80, "🟧"], [0, "🟥"]];

def COMMITS_ROW: "Commits green";

# Mermaid's default plot colour is too pale to see as a line.
def GREEN: "#2da44e";
def RED: "#cf222e";


# Checks

# What requested a check, from its text: `Envoy/Checks (pr/49230/release/v1.37@08dc2dd)`
# or `Envoy/Checks (postsubmit/main@1e013e6)`. A check which never started has
# none.
def context:
  [(.text // "") | match("\\((postsubmit|pr)/([^)\\s]*)@[0-9a-f]+\\)")]
  | first
  | if . then {kind: .captures[0].string, ref: .captures[1].string} else null end;

# Jobs which are allowed to fail do not fail their check, which says so in its
# text instead: `Allowed-to-fail checks failed: build-openssl`
def allowed:
  [(.text // "") | match("Allowed-to-fail checks failed: *([\\w ,-]+)")]
  | first
  | if . then [.captures[0].string | scan("[\\w-]+")] else [] end;

def outcome:
  if .status != "COMPLETED" then
    "pending"
  else
    ((.conclusion // "") | ascii_downcase) as $conclusion
    | if (OUTCOMES + ["skipped"] | index($conclusion)) then $conclusion else "other" end
  end;

def is_digits: test("^[0-9]+$");

# A fetched commit as its checks for the branch, or nothing if it is not the
# branch's.
#
# A stack which is merged without being rewritten keeps its commit ids, so the
# head commit also carries the checks of its pull request, and a new release
# branch starts with the commits, and checks, of the branch it was cut from.
def commit($branch):
  ([.checks[]
    | . as $check
    | context as $context
    | select($context)
    | [$check, $context]]) as $known
  | ([$known[]
      | select(.[1] == {kind: "postsubmit", ref: $branch})
      | .[0]
      | outcome as $outcome
      # Skipped means nothing was run for this commit.
      | select($outcome != "skipped")
      | {workflow: .name,
         outcome: $outcome,
         run_id: ((.run_id // "") | tostring),
         allowed: allowed}]) as $checks
  | (any($known[]; .[1].kind == "postsubmit" and .[1].ref != $branch)) as $elsewhere
  | if $elsewhere and ($checks | length) == 0 then
      # Pushed to another branch, before this one was cut from it.
      empty
    else
      {sha, date, title, checks: $checks}
    end;

def commits($branch): [.[] | commit($branch)];

# The runs whose jobs are wanted: those which failed, or had a job which was
# allowed to.
def runs:
  [.branches
   | to_entries[]
   | .key as $branch
   | .value
   | commits($branch)[]
   | .checks[]
   | select((.outcome == "failure" or (.allowed | length) > 0) and (.run_id | is_digits))
   | .run_id]
  | unique;

# `Check (postsubmit/main@1e013e6) / asan / ...` -> `Check / asan / ...`
def job_name: gsub("\\s*\\((?:postsubmit|pr)/[^)]*\\)"; "");

# Add the names of the run's failed jobs to a check, apart from those which
# were allowed to fail.
def with_jobs($jobs):
  if $jobs == null then
    .
  else
    ([$jobs[] | select(.conclusion == "failure") | .name | job_name] | sort) as $failed
    | ([.allowed[]
        | ascii_downcase
        | split("[-_]"; null)[]
        | select(. != "" and (. as $word | GENERIC_WORDS | index($word) | not))]
       | unique) as $words
    | ([$failed[]
        | select(ascii_downcase as $job
                 | any($words[]; . as $word | $job | contains($word)))]) as $allowed
    | .allowed_jobs = $allowed
    | if .outcome == "failure" then
        ($failed - $allowed) as $required
        | .failed_jobs = (($required - [FINISH_JOB]) | if length > 0 then . else $required end)
      else . end
  end;


# Rates

def counter: OUTCOMES | map({key: ., value: 0}) | from_entries;

def round2: . * 100 | round | . / 100;

# Cancelled is not a pass.
def rate:
  (.success + .failure + .cancelled) as $total
  | if $total > 0 then (100 * .success / $total | round2) else null end;

def commits_rate($with_ci; $not_green):
  if $with_ci > 0 then (100 * ($with_ci - $not_green) / $with_ci | round2) else null end;

def with_rate: . + {pass_rate: rate};

def sum(counters):
  reduce counters as $counts (
    counter;
    reduce OUTCOMES[] as $outcome (.; .[$outcome] += ($counts[$outcome] // 0)))
  | with_rate;

# Entries which have the same name, added up and with the most first.
def most_common:
  reduce .[] as $name ({}; .[$name] += 1)
  | to_entries
  | sort_by(-.value)
  | from_entries;

def by_name(f): group_by(f) | map({key: (.[0] | f), value: .}) | from_entries;

# Outcomes per workflow, a list as a commit can be requested more than once.
def by_workflow:
  sort_by(if (.run_id | is_digits) then (.run_id | tonumber) else 0 end)
  | reduce .[] as $check ({}; .[$check.workflow] += [$check.outcome]);

def not_green: any(.checks[]; .outcome == "failure" or .outcome == "cancelled");

def counts(checks; f):
  [checks]
  | by_name(f)
  | map_values(sum(.[] | {(.outcome): 1}));

def jobs_of(checks):
  [checks]
  | by_name(.workflow)
  | map_values(map(.jobs[]) | most_common);

# A branch's commits, with their checks, as its pass rates.
def aggregate:
  . as $commits
  | ([$commits[] | select(.checks | length > 0)] | length) as $with_ci
  | ([$commits[] | select(not_green)] | length) as $not_green
  | ([$commits[]
      | . as $commit
      | .checks[]
      | select(.allowed | length > 0)
      | {sha: $commit.sha,
         date: $commit.date,
         workflow,
         run_id,
         # Not a failure of the check, so not in any rate, but worth seeing.
         jobs: (if ((.allowed_jobs // []) | length) > 0 then
                  .allowed_jobs
                else
                  .allowed
                end)}]) as $allowed
  | ([$commits[]
      | . as $commit
      | .checks[]
      | select(.outcome == "failure")
      | {sha: $commit.sha,
         date: $commit.date,
         workflow,
         run_id,
         jobs: (.failed_jobs // [])}]) as $failures
  | {commits: ($commits | length),
     commits_with_ci: $with_ci,
     commits_not_green: $not_green,
     commits_pass_rate: commits_rate($with_ci; $not_green),
     total: sum($commits[].checks[] | {(.outcome): 1}),
     groups: counts($commits[].checks[]; .workflow | split("/")[0]),
     workflows: counts($commits[].checks[]; .workflow),
     failed_jobs: jobs_of($failures[]),
     allowed_failed_jobs: jobs_of($allowed[]),
     history: ($commits | sort_by(.date) | map({sha, date, checks: (.checks | by_workflow)})),
     days: ($commits
            | by_name(.date[:10])
            | map_values(
                ([.[] | select(.checks | length > 0)] | length) as $day_with_ci
                | ([.[] | select(not_green)] | length) as $day_not_green
                | {commits: length,
                   commits_with_ci: $day_with_ci,
                   commits_not_green: $day_not_green,
                   commits_pass_rate: commits_rate($day_with_ci; $day_not_green),
                   workflows: counts(.[].checks[]; .workflow)})),
     failures: $failures,
     allowed_failures: $allowed};

# Fetched commits, checks and jobs as a report.
def report($jobs):
  . as $raw
  | del(.branches, .jobs)
  | .schema = SCHEMA
  | .branches = (
      $raw.branches
      | to_entries
      | map(.key as $branch
            | .value |= (commits($branch) | map(.checks |= map(with_jobs($jobs[.run_id]))))
            # A release branch has the history of `main` from before it was cut,
            # so having commits in the period does not mean it existed.
            | select($branch == "main" or any(.value[]; .checks | length > 0))
            | .value |= aggregate)
      | from_entries);

def report: report(.jobs // {});


# Years

def version_key: [scan("\\d+") | tonumber];

# One branch's data for a year, from its data for each month.
def merge:
  . as $parts
  | def summed(f):
      ([$parts[] | f | keys_unsorted[]] | unique) as $names
      | [$names[] as $name | {key: $name, value: sum($parts[] | f | .[$name] // {})}]
      | from_entries;
    def counted(f):
      [$parts[] | f | to_entries[]]
      | by_name(.key)
      | map_values(
          reduce (.[].value | to_entries[]) as $job ({}; .[$job.key] += $job.value)
          | to_entries
          | sort_by(-.value)
          | from_entries);
    ([$parts[].commits_with_ci] | add) as $with_ci
    | ([$parts[].commits_not_green] | add) as $not_green
    | {commits: ([$parts[].commits] | add),
       commits_with_ci: $with_ci,
       commits_not_green: $not_green,
       commits_pass_rate: commits_rate($with_ci; $not_green),
       total: sum($parts[].total),
       groups: summed(.groups),
       workflows: summed(.workflows),
       failed_jobs: counted(.failed_jobs),
       allowed_failed_jobs: counted(.allowed_failed_jobs),
       # Per commit, which a year has too many of to show.
       history: [],
       days: ([$parts[].days | to_entries | sort_by(.key)[]] | from_entries),
       failures: [$parts[].failures[]],
       allowed_failures: [$parts[].allowed_failures[]]};

# The reports of months as the report of a year. GitHub keeps neither checks
# nor workflow runs for that long, so a year cannot be fetched.
#
# The input is the monthly reports, and `$frame` is `{repo, frame, generated}`
# with `frame` the year: reports of other years, periods and repositories are
# ignored. It is an error if the year's monthly reports are all for other
# repositories, as that is most likely the wrong `repo`.
def year($frame):
  . as $reports
  | ($frame.frame | tostring) as $year
  | "\($year)-01-01T00:00:00Z" as $since
  | "\(($year | tonumber) + 1)-01-01T00:00:00Z" as $until
  | ($frame.generated >= $until) as $complete
  | [$reports[] | select(.period == "month" and (.frame | startswith("\($year)-")))] as $found
  | [$found[] | select(.repo == $frame.repo)] as $months
  | if ($months | length) == 0 and ($found | length) > 0 then
      # Easily done when running from a fork or a staging repository.
      error(
        "The monthly reports for \($year) are for "
        + ([$found[].repo] | unique | join(", "))
        + ", not \($frame.repo)")
    elif any($months[]; .schema != SCHEMA) then
      error(
        "The report for "
        + ([$months[] | select(.schema != SCHEMA) | .frame] | join(", "))
        + " does not have schema \(SCHEMA): it needs regenerating")
    else
      # The last one wins should a month be there twice.
      ($months | by_name(.frame) | map_values(last)) as $by_month
      | ([range(1; 13) | "\($year)-\(if . < 10 then "0" else "" end)\(.)"]
         | if $complete then . else map(select(. <= $frame.generated[:7])) end) as $expected
      | ([$by_month[].branches | keys_unsorted[]]
         | unique
         | sort_by([. != "main", (version_key | map(-.))])) as $branches
      | {schema: SCHEMA,
         repo: $frame.repo,
         period: "year",
         frame: $year,
         complete: $complete,
         generated: $frame.generated,
         since: $since,
         until: $until,
         branches: ([$branches[] as $branch
                     | {key: $branch,
                        value: ([$by_month[].branches[$branch] | select(.)] | merge)}]
                    | from_entries),
         months: ($by_month | keys),
         missing: ($expected - ($by_month | keys))}
    end;


# Dates

def day_time: strptime("%Y-%m-%d") | mktime;

def to_day: strftime("%Y-%m-%d");

# The Sunday which starts the week a day is in.
def week_of: day_time | . - (gmtime[6] * 86400) | to_day;

# The days of the period so far.
def days:
  .since[:10] as $since
  | (if .complete then
       .until[:10]
     else
       # To date: the days which have not happened yet are not part of it.
       [.until[:10], (.generated[:10] | day_time + 86400 | to_day)] | min
     end) as $stop
  | [$since
     | day_time
     | recurse(. + 86400; (. | to_day) < $stop)
     | to_day
     | select(. < $stop)];

def grouped(f):
  reduce .[] as $day ([]; ($day | f) as $key
                         | if length > 0 and last.key == $key then
                             last.value += [$day]
                           else
                             . + [{key: $key, value: [$day]}]
                           end);

def month_label: day_time | strftime("%b");

def week_label: day_time | strftime("%b") + " " + (gmtime[2] | tostring);

# The days of the period so far, as weeks from Sunday.
def weeks:
  .since[:10] as $since
  | days
  | grouped([week_of, $since] | max)
  | map(.key |= week_label);

# The days of the period so far, as months.
def months: days | grouped(month_label);

# The days of the period so far as months, each as its weeks from Sunday. A
# week which crosses into the next month is split between them.
def months_of_weeks: months | map(.value |= (grouped(week_of) | map(.value)));


# Summary

def pad1: if test("\\.") then . else . + ".0" end;

def fixed1: . * 10 | round | . / 10 | tostring | pad1;

def pct: if . == null then "-" else "\(fixed1)%" end;

def at_least($scale): . as $rate | first($scale[] | select($rate >= .[0]) | .[1]);

# The rate as coloured text, which in GitHub Markdown takes inline math.
def coloured:
  if . == null then
    ""
  else
    " $`\\color{\(at_least(RATE_COLOURS))}{\\textsf{\(fixed1)\\%}}`$ of commits green"
  end;

def rate_cell: if . == null then NO_CHECK else at_least(RATE_CELLS) end;

def row($name):
  "| \($name) | \(.success) | \(.failure) | \(.cancelled) | \(.pass_rate | pct) |";

# Workflows which were not all green, and the rest.
def noisy: [.workflows | to_entries[] | select(.value.failure > 0 or .value.cancelled > 0) | .key];

def quiet: noisy as $noisy | (.workflows | keys_unsorted) - $noisy;

# `$rows` are `[name, [cell, ...]]`.
def table($first; $heads; $rows):
  ["| \($first) | \($heads | join(" | ")) |",
   "|---|" + ("---|" * ($heads | length)),
   ($rows[] | "| \(.[0]) | \(.[1] | join(" | ")) |"),
   ""];

# A cell per tested commit, in push order, for each workflow which was not all
# green.
def strip:
  noisy as $noisy
  # Only the head commit of a push is tested.
  | ([.history[] | select(.checks | length > 0)]
     | map(. + {day: .date[:10]})
     | grouped(.day)) as $days
  | if ($days | length) == 0 or ($noisy | length) == 0 then
      []
    else
      table(
        "Workflow";
        [$days[].key | day_time | strftime("%a") + " " + strftime("%d")];
        [$noisy[] as $name
         | [$name,
            [$days[].value
             | map(.checks[$name]
                   | if . then map(CELLS[.]) | join("") else NO_CHECK end)
             | join("")]]])
      + ["One cell per commit, oldest first: \(CELLS.success) passed, "
         + "\(CELLS.failure) failed, \(CELLS.cancelled) cancelled, "
         + "\(CELLS.pending) not finished, \(NO_CHECK) not run. "
         + "Commits with no CI are left out.",
         ""]
    end;

# Pass rate over some days, of commits or (with a name) of a workflow.
def over($days; $name):
  [.days[$days[]] | select(.)] as $found
  | if $name == null then
      commits_rate([$found[].commits_with_ci] | add // 0; [$found[].commits_not_green] | add // 0)
    else
      sum($found[].workflows[$name] | select(.)) | .pass_rate
    end;

# A cell per day or week, coloured by pass rate, for each workflow not all
# green. `$groups` are the columns as `{key, value}`, each value a list of
# cells, each the days the cell covers.
def grid($groups; $first; $cell):
  . as $data
  | table(
      $first;
      [$groups[].key];
      [(null, noisy[]) as $name
       | [($name // COMMITS_ROW),
          [$groups[].value | map(. as $days | $data | over($days; $name) | rate_cell) | join("")]]])
  + ["One cell per \($cell), by pass rate: "
     + ([RATE_CELLS[]
         | "\(.[1]) "
           + (if .[0] == 100 then "100%" elif .[0] > 0 then "\(.[0])% or more" else "less" end)]
        | join(", "))
     + ", \(NO_CHECK) nothing run.",
     ""];

def chart($colour; $lines):
  ["```mermaid",
   "%%{init: {\"themeVariables\": {\"xyChart\": {\"plotColorPalette\": \"\($colour)\"}}}}%%",
   $lines[],
   "```",
   ""];

# Pass rates per week or month: a table with each noisy workflow, and a chart
# of commits. `$buckets` are `{key, value}` with the days of each.
def trend($buckets; $unit):
  . as $data
  | table(
      "Per \($unit)";
      [$buckets[].key];
      [(null, noisy[]) as $name
       | [($name // COMMITS_ROW),
          [$buckets[].value as $days | $data | over($days; $name) | pct]]])
  + ([$buckets[]
      | .value as $days
      | {key, value: ($data | over($days; null))}
      | select(.value != null)]
     # A flat line at 100% says nothing, and is hard to see.
     | if length > 1 and ([.[].value] | min) < 100 then
         chart(
           GREEN;
           ["xychart-beta",
            "    title \"Commits green per \($unit)\"",
            "    x-axis [\(map("\"\(.key)\"") | join(", "))]",
            "    y-axis \"%\" 0 --> 100",
            "    line [\(map(.value | tostring) | join(", "))]"])
       else [] end);

# `Check / Release (x64) / [x64] ./ci/do_ci.sh release.test_only` ->
# `release.test_only [x64]`
def job_label:
  split(" / ")
  | last
  | (capture("^(?<arch>\\[\\w+\\]) (?<rest>.*)$") // {arch: null, rest: .})
  | .arch as $arch
  | .rest
  | if startswith("./ci/do_ci.sh ") then ltrimstr("./ci/do_ci.sh ") else . end
  | if startswith("bazel ") then ltrimstr("bazel ") else . end
  | if $arch then "\(.) \($arch)" else . end
  | gsub("\""; "'");

# The most failed jobs, and how often each failed in each week or month.
def jobs_trend($buckets):
  ([$buckets[] | .key as $bucket | .value[] | {key: ., value: $bucket}]
   | from_entries) as $bucket_of
  | ([.failures[]
      | $bucket_of[.date[:10]] as $bucket
      | .jobs[]
      | {job: job_label, $bucket}]
     | by_name(.job)
     | to_entries
     | sort_by([-(.value | length), .key])
     | .[:TREND_JOBS]) as $top
  | if ($top | length) == 0 then
      []
    else
      table(
        "Failed job";
        [$buckets[].key] + ["Total"];
        [$top[]
         | .value as $failed
         | ["`\(.key)`",
            [($buckets[].key as $bucket
              | [$failed[] | select(.bucket == $bucket)]
              | length
              | if . > 0 then tostring else "" end),
             ($failed | length | tostring)]]])
    end;

# The jobs of `failed_jobs` or `allowed_failed_jobs`, the most failed first.
def ranked:
  [to_entries[] | .key as $workflow | .value | to_entries[] | {count: .value, $workflow, job: .key}]
  | sort_by([-.count, .workflow, .job]);

# Mermaid bar chart of the most failed jobs.
def job_chart:
  if length == 0 then
    []
  else
    .[:CHART_JOBS]
    | map(. + {label: (.job | job_label)}) as $jobs
    | chart(
        RED;
        ["xychart-beta horizontal",
         "    title \"Failed jobs\"",
         # Categories have to be unique.
         "    x-axis [\($jobs
                         | map(.label as $name
                               | if ([$jobs[] | select(.label == $name)] | length) > 1 then
                                   "\"\(.label) (\(.workflow))\""
                                 else
                                   "\"\(.label)\""
                                 end)
                         | join(", "))]",
         # Mermaid picks about ten ticks, which below ten are fractions of a failure.
         "    y-axis \"Failures\" 0 --> \([$jobs[0].count, 10] | max)",
         "    bar [\($jobs | map(.count | tostring) | join(", "))]"])
  end;

def jobs_table:
  ["| Workflow | Job | Failures |",
   "|---|---|---:|",
   (.[] | "| \(.workflow) | \(.job) | \(.count) |")];

def frame_text:
  (.since[:10] | day_time) as $since
  | ({year: ($since | strftime("%Y")),
      month: ($since | strftime("%B %Y")),
      week: "week of \(.since[:10])"}[.period]) as $text
  | if .complete then $text else "\($text) to date" end;

def branch_summary($report; $branch):
  . as $data
  | noisy as $noisy
  | (if $report.period == "month" then
       {buckets: ($report | weeks),
        unit: "week",
        groups: ($report | weeks | map(.value |= map([.]))),
        first: "Per day, weeks from Sunday",
        cell: "day"}
     elif $report.period == "year" then
       {buckets: ($report | months),
        unit: "month",
        groups: ($report | months_of_weeks),
        first: "Per week, from Sunday",
        cell: "week"}
     else null end) as $view
  | (.failed_jobs | ranked) as $jobs
  | (.allowed_failed_jobs | ranked) as $allowed
  | ["## `\($branch)`\(.commits_pass_rate | coloured)",
     "",
     "\(.commits) commits, \(.commits_with_ci) with CI, "
     + "\(.commits_not_green) with a failed or cancelled workflow "
     + "(\(.commits_pass_rate | pct) of commits fully passed).",
     ""]
  + if .commits_with_ci == 0 then
      []
    else
      ["| Workflow | Pass | Fail | Cancelled | Pass rate |",
       "|---|---:|---:|---:|---:|",
       (.workflows | to_entries[] | .key as $name | .value | row($name)),
       (.groups | to_entries[] | .key as $name | .value | row("**\($name)/\\***")),
       (.total | row("**All jobs**")),
       ""]
      + (if $view == null then
           strip
         elif ($noisy | length) > 0 then
           # With nothing but passes these are only so many green cells.
           grid($view.groups; $view.first; $view.cell) + trend($view.buckets; $view.unit)
         else [] end)
      + (quiet | if length > 0 then ["No failures: \(join(", ")).", ""] else [] end)
      + ($jobs | job_chart)
      + (if $view then jobs_trend($view.buckets) else [] end)
      + (if ($allowed | length) > 0 then
           ["Allowed to fail, and not counted above:", ""] + ($allowed | jobs_table) + [""]
         else [] end)
      + (if ($jobs | length) > 0 then
           ["<details><summary>Failed jobs</summary>", ""]
           + ($jobs[:TOP_JOBS] | jobs_table)
           + ["", "</details>", ""]
         else [] end)
    end;

# A report as GitHub Markdown, as for a job summary.
def summary:
  . as $report
  | ["# Postsubmit CI report: \(frame_text)", ""]
  + (if ((.missing // []) | length) > 0 then
       ["No data for: \(.missing | join(", ")).", ""]
     else [] end)
  + [.branches | to_entries[] | .key as $branch | .value | branch_summary($report; $branch)[]]
  | join("\n");


# Slack

def lpad($width): tostring | (" " * ([$width - length, 0] | max) // "") + .;

def rpad($width): tostring | . + (" " * ([$width - length, 0] | max) // "");

# The most failed of `failed_jobs` or `allowed_failed_jobs`, by short name.
def labelled:
  [to_entries[].value | to_entries[]]
  | by_name(.key | job_label)
  | to_entries
  | map({job: .key, count: ([.value[].value] | add)})
  | sort_by(-.count)
  | .[:5]
  | map("`\(.job)` \(.count)")
  | join(", ");

def slack_branch($frame; $branch):
  noisy as $noisy
  | quiet as $quiet
  | ([.workflows | to_entries[] | select(.key as $name | $noisy | index($name))]
     + [.groups | to_entries[] | .key |= "\(.)/* (all)"]) as $rows
  | ([$rows[].key | length] | max) as $width
  | ["*Postsubmit CI on `\($branch)`, \($frame)*",
     "CI ran on \(.commits_with_ci) commits: \(.commits_pass_rate | pct) fully "
     + "passed, \(.commits_not_green) had a failed or cancelled workflow.",
     "```\n"
     + ([$rows[]
         | "\(.key | rpad($width))  \(.value.pass_rate | pct | lpad(6))  "
           + "\(.value.failure | lpad(3)) failed"
           + (if .value.cancelled > 0 then ", \(.value.cancelled) cancelled" else "" end)]
        | join("\n"))
     + "\n```"]
  + (if ($quiet | length) > 0 then
       ["\($quiet | length) other workflows had no failures."]
     else [] end)
  + (if (.failed_jobs | length) > 0 then
       ["Most failed jobs: \(.failed_jobs | labelled)"]
     else [] end)
  + (if (.allowed_failed_jobs | length) > 0 then
       ["Allowed to fail, not counted: \(.allowed_failed_jobs | labelled)"]
     else [] end)
  | join("\n");

# A report as the payload for Slack's `chat.postMessage`: the headline numbers
# per branch and, with a `$url`, a link to the rest.
def slack($channel; $url):
  frame_text as $frame
  | ([.branches
      | to_entries[]
      | select(.value.commits_with_ci > 0)
      | .key as $branch
      | .value
      | slack_branch($frame; $branch)]
     | if length == 0 then ["*Postsubmit CI, \($frame)*\nNo commits with CI."] else . end
     | if ($url // "") != "" then . + ["<\($url)|Full report>"] else . end) as $texts
  | {channel: $channel,
     text: "Postsubmit CI report, \($frame)",
     blocks: ($texts | map({type: "section", text: {type: "mrkdwn", text: .}}))};
