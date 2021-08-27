from mypy.plugin import Plugin
from mypy.types import Instance


class AbstractionPlugin(Plugin):

    def get_class_decorator_hook(self, fullname: str):

        def _decorator_hook(*la):
            impl = la[0].cls.info
            iface = la[0].reason.args[0].node
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

        if fullname == "abstracts.decorators.implementer":
            return _decorator_hook


def plugin(version: str):
    return AbstractionPlugin
