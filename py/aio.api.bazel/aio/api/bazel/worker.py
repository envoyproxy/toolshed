
import abstracts

from aio.api.bazel import abstract, interface


@abstracts.implementer(interface.IBazelWorkerProcessor)
class BazelWorkerProcessor(abstract.ABazelWorkerProcessor):
    pass


@abstracts.implementer(interface.IBazelWorker)
class BazelWorker(abstract.ABazelWorker):

    @property
    def processor_class(self):
        return BazelWorkerProcessor
