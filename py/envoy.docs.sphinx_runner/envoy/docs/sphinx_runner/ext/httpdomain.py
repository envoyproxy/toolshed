
import logging

from pygments.lexers import get_lexer_by_name  # type:ignore
from pygments.util import ClassNotFound  # type:ignore

from sphinxcontrib.httpdomain import (  # type:ignore
    HTTPDomain as _HTTPDomain,
    HTTPLexer,
    register_routingtable_as_label)


logger = logging.getLogger(__name__)


class HTTPDomain(_HTTPDomain):

    def merge_domaindata(self, docnames, otherdata):
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
                    'other instance is in %s'
                    % (typ, entry_point_name,
                       self.env.doc2path(other_data[entry_point_name][0]),
                       self.env.doc2path(self_data[entry_point_name][0])))


def setup(app):
    app.add_domain(HTTPDomain)
    app.connect('doctree-read', register_routingtable_as_label)

    try:
        get_lexer_by_name('http')
    except ClassNotFound:
        app.add_lexer('http', HTTPLexer())
    app.add_config_value('http_index_ignore_prefixes', [], None)
    app.add_config_value('http_index_shortname', 'routing table', True)
    app.add_config_value('http_index_localname', 'HTTP Routing Table', True)
    app.add_config_value('http_strict_mode', True, None)
    app.add_config_value('http_headers_ignore_prefixes', ['X-'], None)
    return {"parallel_read_safe": True,
            "parallel_write_safe": True}
