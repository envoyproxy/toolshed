from mypy.nodes import TupleExpr
from mypy.plugin import Plugin
from mypy.types import Instance


class AbstractionPlugin(Plugin):

    def _decorator_hook(self, *la):
        impl = la[0].cls.info
        for iface in la[0].reason.args:
            if not isinstance(iface, TupleExpr):
                self._decorate_klass(impl, iface.node)
                continue
            for _iface in iface.items:
                self._decorate_klass(impl, _iface.node)

    def _decorate_klass(self, impl, iface):
        try:
            # not sure if this is necessary
            Instance(iface, [])
        except TypeError:
            return
        # TODO: this needs to discriminate between ifaces and
        #   abstractions
        impl.mro += [
            base for base
            in iface.mro
            if base not in impl.mro]

    def get_class_decorator_hook(self, fullname: str):
        if fullname == "abstracts.decorators.implementer":
            return self._decorator_hook


def plugin(version: str):
    return AbstractionPlugin
