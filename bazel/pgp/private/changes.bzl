"""Cacheable Debian `.changes` transformations."""

def _pgp_changes_split_impl(ctx):
    src = ctx.file.src
    out = ctx.outputs.out
    ctx.actions.run_shell(
        inputs = [src],
        outputs = [out],
        arguments = [src.path, out.path, ctx.attr.distro],
        command = """\
set -eu
src="$1"
out="$2"
distro="$3"

if ! grep -q '^Distribution:' "$src"; then
    echo "missing Distribution: line in $src" >&2
    exit 1
fi
awk -v distro="$distro" \
    '/^Distribution:/ { print "Distribution: " distro; next } { print }' \
    "$src" > "$out"
""",
        mnemonic = "OpenPGPChangesSplit",
        progress_message = "Splitting Debian changes %s for %s" % (src.short_path, ctx.attr.distro),
    )
    return [DefaultInfo(files = depset([out]))]

pgp_changes_split = rule(
    implementation = _pgp_changes_split_impl,
    attrs = {
        "distro": attr.string(mandatory = True),
        "out": attr.output(mandatory = True),
        "src": attr.label(mandatory = True, allow_single_file = True),
    },
)
