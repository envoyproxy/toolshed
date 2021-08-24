from mypy.plugin import Plugin
from mypy.nodes import SymbolTable, TypeInfo
from mypy.types import Instance


class AbstractionPlugin(Plugin):

    def get_class_decorator_hook(self, fullname: str):

        def _decorator_hook(*la):
            impl = la[0].cls.info
            iface = la[0].reason.args[0].node
            try:
                promote = Instance(iface, [])
            except TypeError:
                return
            if not any(ti._promote == promote for ti in impl.mro):
                faketi = TypeInfo(SymbolTable(), iface.defn, iface.module_name)
                faketi._promote = promote
                impl.mro.append(faketi)

        if fullname == "abstracts.decorators.implementer":
            return _decorator_hook


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return AbstractionPlugin
