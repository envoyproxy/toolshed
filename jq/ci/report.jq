import "ci/checks" as checks;

# Jobs fetched after the commits can be given as `--slurpfile jobs`.
checks::report($ARGS.named.jobs[0] // .jobs // {})
