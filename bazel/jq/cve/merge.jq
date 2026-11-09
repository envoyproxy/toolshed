import "cve/utils" as utils;

# $nvd: `{matches, analyzed}` (from `cve/nvd_scan.jq`, slurped), input: CVE Program matches
utils::merge_sources($nvd[0]; .)
