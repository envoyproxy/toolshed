# Deliberately produces no output; used by the "missing_output" target to
# exercise the genrule's declared-output check (see certs_analysis_test.bzl).
[cert unused]
key = ca_key.pem
cfg = ca.cfg
out = none
