"""Per-test lcov merger that strips the records the combined report does not read."""

DEFAULT_STRIP_RECORDS = [
    # Function definitions, hit counts and their per-file totals.
    "FN",
    "FNDA",
    "FNF",
    "FNH",
    # Branch data and totals.
    "BRDA",
    "BRF",
    "BRH",
]

def _runfile_key(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _lcov_merger_impl(ctx):
    merger = ctx.attr.merger[DefaultInfo]
    if not ctx.attr.strip:
        fail("lcov_merger needs at least one record type to strip; use the merger directly otherwise")
    for record in ctx.attr.strip:
        if not record or not record.isalnum() or not record.isupper():
            fail("lcov record names are upper-case alphanumerics: %r" % record)
    output = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.expand_template(
        template = ctx.file._script,
        output = output,
        substitutions = {
            "{{MERGER}}": _runfile_key(ctx, merger.files_to_run.executable),
            "{{STRIP}}": " ".join(ctx.attr.strip),
            "{{CLEAN}}": "1" if ctx.attr.clean_coverage_dir else "0",
        },
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [merger.files_to_run.executable])
    runfiles = runfiles.merge(merger.default_runfiles)
    runfiles = runfiles.merge(ctx.attr._runfiles[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = output, runfiles = runfiles)]

lcov_merger = rule(
    implementation = _lcov_merger_impl,
    executable = True,
    doc = """Wraps a Bazel lcov merger and strips records from the merged per-test report.

Point `--coverage_output_generator` at an instance of this rule. Arguments are passed
through to `merger`; the `--output_file` it writes is then filtered in place, dropping
every lcov record type named in `strip`. The default drops function and branch records,
which the toolshed report and threshold validation never read, and keeps every `DA`
line record, including zero-hit lines. Inside the test action (no split postprocessing)
it also clears the coverage directory's intermediates after merging, so they are not
uploaded with the test's outputs.
""",
    attrs = {
        "merger": attr.label(
            default = "@bazel_tools//tools/test:lcov_merger",
            executable = True,
            # Runs alongside the wrapper, in whatever configuration the wrapper was built for
            # (the test exec group when selected by --coverage_output_generator).
            cfg = "target",
            doc = "The merger to wrap, normally Bazel's own.",
        ),
        "strip": attr.string_list(
            default = DEFAULT_STRIP_RECORDS,
            doc = "lcov record types (the text before the colon) to drop from the merged report.",
        ),
        "clean_coverage_dir": attr.bool(
            default = True,
            doc = """Remove the coverage directory's intermediates (raw profiles, the unfiltered
export, indexed profiles) once the report is merged, when the merger runs inside the test
action rather than in a split postprocessing spawn. Without split postprocessing that
directory is uploaded with the test's outputs, and these files are its bulk.""",
        ),
        "_runfiles": attr.label(default = "@bazel_tools//tools/bash/runfiles"),
        "_script": attr.label(
            default = "//coverage:lcov_merger.sh",
            allow_single_file = True,
        ),
    },
)
