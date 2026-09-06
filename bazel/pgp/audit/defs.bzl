"""Hermetic OpenPGP signing audit rules."""

load("@bazel_skylib//lib:shell.bzl", "shell")

_JQ_TOOLCHAIN_TYPE = "@aspect_bazel_lib//lib:jq_toolchain_type"

_DEFAULT_MNEMONIC = "OpenPGPSign"
_DEFAULT_REQUIRED_EXECUTION_REQUIREMENTS = [
    "no-cache",
    "no-remote",
    "no-remote-cache",
    "no-remote-cache-upload",
    "no-remote-exec",
]
_DEFAULT_FORBIDDEN_ENV = [
    "GNUPGHOME",
    "HOME",
    "SSH_AUTH_SOCK",
]
_DEFAULT_FORBIDDEN_INPUTS_REGEX = "(^|/)\\.gnupg(/|$)|private-keys-v1\\.d|passphrase|secret|\\.(asc|pgp|gpg|key)$"

def _json_string_list(values):
    return json.encode(values)

def _runfiles_path(ctx, file):
    path = file.short_path
    if path.startswith("../"):
        return path[3:]
    return "%s/%s" % (ctx.workspace_name, path)

def _jq_args(ctx, jq_bin):
    args = ctx.actions.args()
    args.add(jq_bin)
    args.add("-L", ctx.file._lib.dirname)
    args.add("-f", ctx.file._filter)
    args.add_all(["--arg", "mnemonic", ctx.attr.mnemonic])
    args.add_all(["--argjson", "required_exec_reqs", _json_string_list(ctx.attr.required_execution_requirements)])
    args.add_all(["--argjson", "forbidden_env", _json_string_list(ctx.attr.forbidden_env)])
    args.add_all(["--arg", "forbidden_inputs_re", ctx.attr.forbidden_inputs_regex])
    args.add_all(["--argjson", "forbidden_strings", _json_string_list(ctx.attr.forbidden_strings)])
    args.add(ctx.file.aquery)
    return args

def _pgp_audit_impl(ctx):
    out = ctx.actions.declare_file("%s.report.json" % ctx.label.name)
    jq_bin = ctx.toolchains[_JQ_TOOLCHAIN_TYPE].jqinfo.bin
    ctx.actions.run_shell(
        command = "out=\"$1\"; shift; \"$@\" > \"$out\"",
        arguments = [out.path, _jq_args(ctx, jq_bin)],
        inputs = [ctx.file.aquery, ctx.file._filter, ctx.file._lib],
        outputs = [out],
        mnemonic = "OpenPGPAudit",
        progress_message = "Auditing OpenPGP signing actions in %s" % ctx.file.aquery.short_path,
        tools = [jq_bin],
    )
    return [DefaultInfo(files = depset([out]))]

pgp_audit = rule(
    implementation = _pgp_audit_impl,
    doc = "Run the OpenPGP signing audit over captured `bazel aquery --output=jsonproto` JSON.",
    attrs = {
        "aquery": attr.label(
            doc = "Captured `bazel aquery --output=jsonproto` JSON.",
            mandatory = True,
            allow_single_file = [".json"],
        ),
        "forbidden_strings": attr.string_list(
            doc = "Strings that must not appear in signing action argv.",
        ),
        "mnemonic": attr.string(default = _DEFAULT_MNEMONIC),
        "required_execution_requirements": attr.string_list(default = _DEFAULT_REQUIRED_EXECUTION_REQUIREMENTS),
        "forbidden_env": attr.string_list(default = _DEFAULT_FORBIDDEN_ENV),
        "forbidden_inputs_regex": attr.string(default = _DEFAULT_FORBIDDEN_INPUTS_REGEX),
        "_filter": attr.label(default = "//pgp/audit:audit.jq", allow_single_file = True),
        "_lib": attr.label(default = "//pgp/audit:lib.jq", allow_single_file = True),
    },
    toolchains = [_JQ_TOOLCHAIN_TYPE],
)

def _pgp_audit_result_test_impl(ctx):
    status = ctx.actions.declare_file("%s.exit_status" % ctx.label.name)
    jq_bin = ctx.toolchains[_JQ_TOOLCHAIN_TYPE].jqinfo.bin
    status_args = ctx.actions.args()
    status_args.add(jq_bin)
    status_args.add("-r")
    status_args.add_all(["--argjson", "want_failures", "true" if ctx.attr.want_failures else "false"])
    status_args.add("if ((.failures | length) > 0) == $want_failures then \"0\" else \"1\" end")
    status_args.add(ctx.file.report)
    ctx.actions.run_shell(
        command = "out=\"$1\"; shift; \"$@\" > \"$out\"",
        arguments = [status.path, status_args],
        inputs = [ctx.file.report],
        outputs = [status],
        mnemonic = "OpenPGPAuditAssert",
        progress_message = "Checking OpenPGP audit result %s" % ctx.file.report.short_path,
        tools = [jq_bin],
    )

    script = ctx.actions.declare_file("%s.sh" % ctx.label.name)
    substitutions = {
        "@REPORT@": shell.quote(_runfiles_path(ctx, ctx.file.report)),
        "@STATUS@": shell.quote(_runfiles_path(ctx, status)),
    }
    ctx.actions.expand_template(
        template = ctx.file._test_template,
        output = script,
        substitutions = substitutions,
        is_executable = True,
    )
    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(files = [ctx.file.report, status]),
    )]

_pgp_audit_result_test = rule(
    implementation = _pgp_audit_result_test_impl,
    test = True,
    attrs = {
        "report": attr.label(mandatory = True, allow_single_file = [".json"]),
        "want_failures": attr.bool(default = False),
        "_test_template": attr.label(default = "//pgp/audit:audit_result_test.sh.tpl", allow_single_file = True),
    },
    toolchains = [_JQ_TOOLCHAIN_TYPE],
)

def pgp_audit_test(name, aquery, expect_failure = False, forbidden_strings = [], **kwargs):
    """Audit captured aquery JSON and fail if the report has unexpected failures."""
    report_name = "%s_report" % name
    pgp_audit(
        name = report_name,
        aquery = aquery,
        forbidden_strings = forbidden_strings,
        **kwargs
    )
    _pgp_audit_result_test(
        name = name,
        report = ":%s" % report_name,
        want_failures = expect_failure,
    )

def _pgp_audit_binary_impl(ctx):
    jq_bin = ctx.toolchains[_JQ_TOOLCHAIN_TYPE].jqinfo.bin
    script = ctx.actions.declare_file("%s.sh" % ctx.label.name)
    substitutions = {
        "@JQ@": shell.quote(_runfiles_path(ctx, jq_bin)),
        "@FILTER@": shell.quote(_runfiles_path(ctx, ctx.file._filter)),
        "@LIB_DIR@": shell.quote(_runfiles_path(ctx, ctx.file._lib).rsplit("/", 1)[0]),
        "@MNEMONIC@": shell.quote(ctx.attr.mnemonic),
        "@REQUIRED_EXEC_REQS@": shell.quote(_json_string_list(ctx.attr.required_execution_requirements)),
        "@FORBIDDEN_ENV@": shell.quote(_json_string_list(ctx.attr.forbidden_env)),
        "@FORBIDDEN_INPUTS_RE@": shell.quote(ctx.attr.forbidden_inputs_regex),
    }
    ctx.actions.expand_template(
        template = ctx.file._launcher_template,
        output = script,
        substitutions = substitutions,
        is_executable = True,
    )
    return [DefaultInfo(
        executable = script,
        runfiles = ctx.runfiles(files = [jq_bin, ctx.file._filter, ctx.file._lib]),
    )]

pgp_audit_binary = rule(
    implementation = _pgp_audit_binary_impl,
    doc = "Runnable OpenPGP audit CLI using jq from the hermetic toolchain.",
    executable = True,
    attrs = {
        "mnemonic": attr.string(default = _DEFAULT_MNEMONIC),
        "required_execution_requirements": attr.string_list(default = _DEFAULT_REQUIRED_EXECUTION_REQUIREMENTS),
        "forbidden_env": attr.string_list(default = _DEFAULT_FORBIDDEN_ENV),
        "forbidden_inputs_regex": attr.string(default = _DEFAULT_FORBIDDEN_INPUTS_REGEX),
        "_filter": attr.label(default = "//pgp/audit:audit.jq", allow_single_file = True),
        "_lib": attr.label(default = "//pgp/audit:lib.jq", allow_single_file = True),
        "_launcher_template": attr.label(default = "//pgp/audit:audit.sh.tpl", allow_single_file = True),
    },
    toolchains = [_JQ_TOOLCHAIN_TYPE],
)
