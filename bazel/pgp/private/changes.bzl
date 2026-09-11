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

def _changes_from_tarball_impl(ctx):
    tarball = ctx.file.tarball
    out = ctx.outputs.out
    ctx.actions.run(
        executable = ctx.executable._extractor,
        inputs = [tarball],
        outputs = [out],
        arguments = [tarball.path, ctx.attr.package, ctx.attr.prefix, out.path],
        tools = [ctx.executable._extractor],
        mnemonic = "OpenPGPChangesExtract",
        progress_message = "Extracting %s_*.changes from %s" % (ctx.attr.package, tarball.short_path),
    )
    return [DefaultInfo(files = depset([out]))]

changes_from_tarball = rule(
    implementation = _changes_from_tarball_impl,
    doc = "Extract one Debian `<package>_*.changes` file from a package tarball.",
    attrs = {
        "tarball": attr.label(
            doc = "Package tarball (`.tar`/`.tar.gz`/`.tar.zst`/etc) containing the `.changes` file.",
            mandatory = True,
            allow_single_file = True,
        ),
        "package": attr.string(
            doc = "Debian source package name, eg `envoy` or `envoy-1.40`.",
            mandatory = True,
        ),
        "prefix": attr.string(
            doc = "Optional directory prefix inside the tarball, eg `deb`.",
            default = "",
        ),
        "out": attr.output(
            doc = "The extracted `.changes` file.",
            mandatory = True,
        ),
        "_extractor": attr.label(
            default = "//pgp/private:changes_extractor",
            executable = True,
            cfg = "exec",
        ),
    },
)
