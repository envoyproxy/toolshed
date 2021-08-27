from mypy.plugin import Plugin


class AbstractionPlugin(Plugin):

    def get_class_decorator_hook(self, fullname: str):

        def _decorator_hook(*la):
            impl = la[0].cls.info
            iface = la[0].reason.args[0].node
            if iface.defn.info not in impl.mro:
                # TODO: this needs to discriminate between ifaces and
                #   abstractions
                impl.mro.append(iface.defn.info)

        if fullname == "abstracts.decorators.implementer":
            return _decorator_hook


def plugin(version: str):
    return AbstractionPlugin
