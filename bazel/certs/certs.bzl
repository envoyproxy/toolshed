"""Bazel rules for generating test certificate fixtures.

Test certificates, CRLs, OCSP responses and related fixtures used to be
checked in and refreshed by hand with scripts that shelled out to the
OpenSSL CLI (and, sometimes, to `faketime`). They can instead be produced at
build time by `//certs:gen`, which links BoringSSL directly and has no
dependency on the consuming workspace.

The generator stamps certificates with a validity window that starts on Jan 1
of a given year, so fixtures never age out of validity. By default that year
is read from `@cert_epoch//:year`, which only changes when the year does, so
the fixtures (and everything built from them) stay cached until then; it can
also be pinned directly via `year`, or read from another file via `year_file`.

See README.md in this package for the full spec file format.
"""

def generated_certs(
        name,
        spec,
        outs,
        srcs = [],
        static_srcs = [],
        headers_name = None,
        gen = Label("//certs:gen"),
        year = None,
        year_file = Label("@cert_epoch//:year"),
        testonly = False,
        tags = [],
        visibility = None):
    """Generates test certificates from `spec` and bundles them into a filegroup.

    Args:
      name: name of the resulting runtime filegroup. Consumers depend on this
        via `data = [...]`. Generated and checked-in `.h` files are excluded
        because headers are compile-time inputs, and rules_apple buckets any
        bundled `.h` resource as a Metal header.
      spec: the fixture spec file consumed by the generator (see README.md
        for the spec format).
      outs: every file the generator writes for this spec. The generator
        fails if the spec asks for an output that is not declared here. Header
        outputs are still declared by the genrule and remain referenceable by
        label, but are excluded from the runtime filegroup.
      srcs: generator inputs (keys, `.cfg` files, password files).
      static_srcs: checked-in fixtures that are not generated but that
        consumers expect to find alongside the generated ones. Checked-in
        headers are excluded from the runtime filegroup for the same reason as
        generated headers.
      headers_name: optional name of an additional filegroup containing only
        generated `.h` outputs, for consumers that prefer to depend on one
        label from `hdrs = [...]` instead of listing each generated header.
      gen: label of the certificate generator binary. Defaults to the one
        provided by this package; overriding it is only useful for testing
        the macro itself. Resolved with `Label()` so the default binds to
        `@envoy_toolshed//certs:gen` regardless of which workspace/module
        loads this macro.
      year: if set, the four digit year fixtures are stamped as starting
        from (Jan 1 of that year). Passed straight to `--year`, and
        `year_file` is not used.
      year_file: label of a file holding the four digit year, used when `year`
        is unset. Defaults to `@cert_epoch//:year`: the host's current UTC year
        when that repo is fetched, or `--repo_env=CERT_EPOCH_YEAR=<YYYY>`. It is
        a regular input, so the generator only reruns when it (or the
        generator, spec or `srcs`) changes.
      testonly: marks the generated targets as test-only.
      tags: tags applied to the generated targets.
      visibility: visibility of the generated targets.
    """
    gen_label = str(Label(str(gen)))

    # No stamping: workspace status files change on every build, which would rerun the generator
    # and bust the cache of everything built from its outputs. The year is a regular input.
    if year != None:
        year_cmd = ""
        year_arg = "\"" + str(year) + "\""
        year_srcs = []
    else:
        year_label = str(native.package_relative_label(year_file))
        year_cmd = "YEAR=$$(tr -d '[:space:]' < $(location " + year_label + "));"
        year_arg = "\"$$YEAR\""
        year_srcs = [year_label]

    native.genrule(
        name = name + "_gen",
        srcs = [spec] + srcs + year_srcs,
        outs = outs,
        cmd = " ".join([
            year_cmd,
            "$(location " + gen_label + ")",
            "--spec $(location " + spec + ")",
            "--in-dir $$(dirname $(location " + spec + "))",
            "--out-dir $(RULEDIR)",
            "--year " + year_arg + ";",
            "missing=\"\";",
            "for out in $(OUTS); do",
            "  if [ ! -e \"$$out\" ]; then missing=\"$$missing $$out\"; fi;",
            "done;",
            "if [ -n \"$$missing\" ]; then",
            "  echo \"" + gen_label + " did not create declared output(s):$$missing\" >&2;",
            "  exit 1;",
            "fi;",
        ]),
        testonly = testonly,
        tags = tags,
        tools = [gen_label],
        visibility = visibility,
    )

    native.filegroup(
        name = name,
        # Generated/checked-in headers are consumed via `hdrs`, not at runtime.
        # Keep them out of the data filegroup: rules_apple buckets any bundled
        # `.h` resource as a Metal header and then fails MetallibCompile with
        # "no input files" when no `.metal` sources accompany them.
        srcs = [f for f in outs + static_srcs if not f.endswith(".h")],
        testonly = testonly,
        tags = tags,
        visibility = visibility,
    )

    if headers_name != None:
        native.filegroup(
            name = headers_name,
            srcs = [f for f in outs if f.endswith(".h")],
            testonly = testonly,
            tags = tags,
            visibility = visibility,
        )
