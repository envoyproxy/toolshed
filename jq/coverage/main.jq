import "coverage/report" as report;

report::report($config[0]; ($source_directories | split("\n") | map(select(. != ""))))
