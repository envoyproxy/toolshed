genrule(
    name = "generated_public_key",
    outs = ["generated-public-key.asc"],
    tools = ["@sq//:sq"],
    cmd = """\
tmp="$$(mktemp -d)"
trap 'rm -rf "$$tmp"' EXIT
$(location @sq//:sq) --batch --home none --cert-store none --key-store none \
    key generate --own-key --without-password --no-userids \
    --rev-cert "$$tmp/key.rev" --output "$$tmp/key.pgp"
$(location @sq//:sq) --batch --home none --cert-store none --key-store none \
    key extract-cert --output "$@" "$$tmp/key.pgp"
""",
)
