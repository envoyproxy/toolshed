import "ci/checks" as checks;

checks::slack($channel; $ARGS.named.url // "")
