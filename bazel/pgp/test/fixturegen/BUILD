genrule(
    name = "generated_public_key",
    outs = ["generated-public-key.asc"],
    target_compatible_with = ["@platforms//os:linux"],
    tools = ["@sq//:sq"],
    cmd = """\
tmp="$$(mktemp -d)"
trap 'rm -rf "$$tmp"' EXIT
$(location @sq//:sq) --batch --home none --cert-store none --key-store none \
    key generate --own-key --without-password --no-userids \
    --rev-cert "$$tmp/key.rev" --output "$$tmp/key.pgp"
$(location @sq//:sq) --batch --home none --cert-store none --key-store none \
    key delete --cert-file "$$tmp/key.pgp" --output "$@"
""",
   visibility = ["//pgp/test:__pkg__"],
)

genrule(
    name = "changes_tarball",
    srcs = ["//pgp/test:fixtures/changes-with-distribution.changes"],
    outs = ["changes-tarball.tar.gz"],
    visibility = ["//pgp/test:__pkg__"],
    cmd = """\
tmp="$$(mktemp -d)"
trap 'rm -rf "$$tmp"' EXIT
mkdir -p "$$tmp/deb"
cp $(location //pgp/test:fixtures/changes-with-distribution.changes) \
    "$$tmp/deb/example_1.0_amd64.changes"
sed 's/^Source:.*/Source: example-contrib/' \
    $(location //pgp/test:fixtures/changes-with-distribution.changes) \
    > "$$tmp/deb/example-contrib_1.0_amd64.changes"
tar czf "$@" -C "$$tmp" deb
""",
)
