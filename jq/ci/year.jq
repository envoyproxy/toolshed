import "ci/checks" as checks;

# Run with `-s` over the monthly reports, and `--arg repo`, `--arg year`.
checks::year({
  repo: $repo,
  frame: $year,
  generated: ($ARGS.named.generated // (now | strftime("%Y-%m-%dT%H:%M:%SZ")))})
