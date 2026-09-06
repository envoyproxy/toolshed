"""Bazel rules for generating test certificate fixtures.

Test certificates, CRLs, OCSP responses and related fixtures used to be
checked in and refreshed by hand with scripts that shelled out to the
OpenSSL CLI (and, sometimes, to `faketime`). They can instead be produced at
build time by `//certs:gen`, which links BoringSSL directly and has no
dependency on the consuming workspace.

The generator stamps certificates with a validity window that starts on Jan 1
of a given year, so fixtures never age out of validity. By default that year
is read hermetically from the consumer's workspace status output (see
`year_status_key` below); it can also be pinned directly via `year`.

See README.md in this package for the full spec file format.
"""

def generated_certs(
        name,
        spec,
        outs,
        srcs = [],
        static_srcs = [],
        gen = Label("//certs:gen"),
        year = None,
        year_status_key = "STABLE_CERT_EPOCH_YEAR",
        fallback_to_host_year = False,
        visibility = None):
    """Generates test certificates from `spec` and bundles them into a filegroup.

    Args:
      name: name of the resulting filegroup. Consumers depend on this via
        `data = [...]`.
      spec: the fixture spec file consumed by the generator (see README.md
        for the spec format).
      outs: every file the generator writes for this spec. The generator
        fails if the spec asks for an output that is not declared here.
      srcs: generator inputs (keys, `.cfg` files, password files).
      static_srcs: checked-in fixtures that are not generated but that
        consumers expect to find alongside the generated ones.
      gen: label of the certificate generator binary. Defaults to the one
        provided by this package; overriding it is only useful for testing
        the macro itself. Resolved with `Label()` so the default binds to
        `@envoy_toolshed//certs:gen` regardless of which workspace/module
        loads this macro.
      year: if set, the four digit year fixtures are stamped as starting
        from (Jan 1 of that year). Passed straight to `--year` and disables
        workspace stamping entirely. Leave unset (the default) to derive the
        year hermetically from the workspace status output at build time.
      year_status_key: the key looked up in `bazel-out/stable-status.txt`
        (i.e. the `--stamp`ed workspace status) to obtain the epoch year
        when `year` is not set. The consumer's `workspace_status_command`
        must print a matching `<year_status_key> <YYYY>` line; see
        README.md for details.
      fallback_to_host_year: if true, and stamping is enabled but
        `year_status_key` is absent from the workspace status output, fall
        back to the (non-hermetic) host date instead of failing the build.
        Defaults to false so that a missing workspace status key is caught
        immediately rather than silently producing fixtures whose validity
        window depends on when the build happened to run.
      visibility: visibility of the generated targets.
    """
    gen_label = str(Label(str(gen)))

    if year != None:
        year_cmd = "YEAR=\"" + str(year) + "\";"
        stamp = 0
    else:
        fallback_cmd = (
            "YEAR=$$(date -u +%Y);"
            if fallback_to_host_year
            else (
                "echo \"missing '" + year_status_key + "' in bazel-out/stable-status.txt; " +
                "ensure your workspace_status_command emits it (see " +
                "@envoy_toolshed//certs:README.md)\" >&2; exit 1;"
            )
        )
        year_cmd = " ".join([
            "YEAR=$$(sed -n -E 's/^" + year_status_key + " (.*)$$/\\1/p'",
            "< bazel-out/stable-status.txt);",
            "if [ -z \"$$YEAR\" ]; then " + fallback_cmd + " fi;",
        ])
        stamp = 1

    native.genrule(
        name = name + "_gen",
        srcs = [spec] + srcs,
        outs = outs,
        cmd = " ".join([
            year_cmd,
            "$(location " + gen_label + ")",
            "--spec $(location " + spec + ")",
            "--in-dir $$(dirname $(location " + spec + "))",
            "--out-dir $(RULEDIR)",
            "--year \"$$YEAR\";",
            "missing=\"\";",
            "for out in $(OUTS); do",
            "  if [ ! -e \"$$out\" ]; then missing=\"$$missing $$out\"; fi;",
            "done;",
            "if [ -n \"$$missing\" ]; then",
            "  echo \"" + gen_label + " did not create declared output(s):$$missing\" >&2;",
            "  exit 1;",
            "fi;",
        ]),
        # Undocumented attr to depend on the workspace status files; see
        # https://github.com/bazelbuild/bazel/issues/4942
        stamp = stamp,
        tools = [gen_label],
        visibility = visibility,
    )

    native.filegroup(
        name = name,
        srcs = outs + static_srcs,
        visibility = visibility,
    )
