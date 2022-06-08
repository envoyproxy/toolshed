
from typing import Dict

from pygments.lexers import PowerShellLexer  # type:ignore


def setup(app) -> Dict:
    app.add_lexer('powershell', PowerShellLexer)
    return dict(parallel_read_safe=True)
