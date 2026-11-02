"""Repository rule providing the epoch year for generated test certificates."""

_YEAR_ENV = "CERT_EPOCH_YEAR"

def _current_utc_year(repository_ctx):
    if repository_ctx.os.name.startswith("windows"):
        cmd = ["powershell", "-NoProfile", "-Command", "(Get-Date).ToUniversalTime().Year"]
    else:
        cmd = ["date", "-u", "+%Y"]
    result = repository_ctx.execute(cmd)
    if result.return_code != 0:
        fail("unable to read the current UTC year with %s: %s" % (cmd, result.stderr))
    return result.stdout.strip()

def _cert_epoch_repo_impl(repository_ctx):
    year = repository_ctx.getenv(_YEAR_ENV) or _current_utc_year(repository_ctx)
    if len(year) != 4 or not year.isdigit():
        fail("certificate epoch year must be four digits, got %r" % year)
    repository_ctx.file("year", year + "\n")
    repository_ctx.file("BUILD.bazel", 'exports_files(["year"])\n')

cert_epoch_repo = repository_rule(
    implementation = _cert_epoch_repo_impl,
    # Deliberately not `reproducible`: the contents depend on when the repo is fetched, so it
    # must not be shared through the repo contents cache. `getenv` tracks CERT_EPOCH_YEAR.
    doc = """Writes the certificate epoch year to `//:year`.

The year is the host's current UTC year when the repo is fetched, or `CERT_EPOCH_YEAR`
(eg `--repo_env=CERT_EPOCH_YEAR=2030`) to pin it. As the file only changes when the year
does, generated certificates, and everything built from them, stay cached until then.
""",
)
