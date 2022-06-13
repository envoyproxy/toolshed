
import abstracts


class IProcessor(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __call__(self, *args):
        raise NotImplementedError


class IStdinStdoutProcessor(IProcessor, metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, processor, stdin=None, stdout=None, log=None):
        raise NotImplementedError


class IProcessProtocol(metaclass=abstracts.Interface):

    @abstracts.interfacemethod
    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    @abstracts.interfacemethod
    async def __call__(self, incoming):
        raise NotImplementedError
