
"""Sphinx HTTP domain customization for Envoy docs."""

import logging
from typing import Any, cast

from pygments.lexers import get_lexer_by_name  # type:ignore[import-untyped]
from pygments.util import ClassNotFound  # type:ignore[import-untyped]
from sphinx.application import Sphinx

from sphinxcontrib.httpdomain import (  # type:ignore[import-untyped]
    HTTPDomain as _HTTPDomain,
    HTTPLexer,
    register_routingtable_as_label)


logger = logging.getLogger(__name__)


class HTTPDomain(_HTTPDomain):

    def merge_domaindata(
            self,
            docnames: list[str],
            otherdata: dict[str, dict[str, tuple[str, ...]]]) -> None:
        """Hacked version of sphinxcontrib.httpdomain to ignore false
        duplicates when building multi-core."""
        for typ in self.object_types:
            self_data = self.data[typ]
            other_data = otherdata[typ]
            for entry_point_name, entry_point_data in other_data.items():
                duplicate = (
                    entry_point_name in self_data
                    and not entry_point_data == self_data[entry_point_name])
                if not duplicate:
                    self_data[entry_point_name] = entry_point_data
                    continue
                logger.warning(
                    'duplicate HTTP %s method definition %s in %s, '
                    'other instance is in %s',
                    typ, entry_point_name,
                    self.env.doc2path(other_data[entry_point_name][0]),
                    self.env.doc2path(self_data[entry_point_name][0]))


def setup(app: Sphinx) -> dict[str, bool]:
    sphinx_app = cast(Any, app)
    sphinx_app.add_domain(HTTPDomain)
    sphinx_app.connect('doctree-read', register_routingtable_as_label)

    try:
        get_lexer_by_name('http')
    except ClassNotFound:
        sphinx_app.add_lexer('http', HTTPLexer())
    sphinx_app.add_config_value('http_index_ignore_prefixes', [], None)
    sphinx_app.add_config_value(
        'http_index_shortname', 'routing table', True)
    sphinx_app.add_config_value(
        'http_index_localname', 'HTTP Routing Table', True)
    sphinx_app.add_config_value('http_strict_mode', True, None)
    sphinx_app.add_config_value('http_headers_ignore_prefixes', ['X-'], None)
    return {"parallel_read_safe": True,
            "parallel_write_safe": True}
