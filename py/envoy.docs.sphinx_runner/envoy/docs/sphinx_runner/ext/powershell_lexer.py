
from typing import Dict

from pygments.lexers import PowerShellLexer

from sphinx.application import Sphinx


def setup(app: Sphinx) -> Dict:
    app.add_lexer('powershell', PowerShellLexer)
    return dict(
        parallel_read_safe=True,
        parallel_write_safe=True)
