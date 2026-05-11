"""PowerShell lexer registration for Envoy docs Sphinx builds."""

from pygments.lexers import PowerShellLexer

from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict:
    app.add_lexer('powershell', PowerShellLexer)
    return dict(
        parallel_read_safe=True,
        parallel_write_safe=True)
