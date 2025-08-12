
class ResponseError(Exception):
    pass


class ToolRequest:
    def __init__(self, ctx, tool_name, *args, **kwargs):
        self.ctx = ctx
        self.tool_name = tool_name
        self.args = args
        self.kwargs = kwargs
        self.data = None
        self.error = None

    async def __aenter__(self):
        await self.debug(dict(
            tool=self.tool_name,
            event="request",
            request_id=self.ctx.request_id,
            args=self.args,
            kwargs=self.kwargs))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.debug(dict(
            tool=self.tool_name,
            event="response",
            request_id=self.ctx.request_id,
            error=self.error,
            data=self.data))
        return False

    async def debug(self, data):
        await self.ctx.debug(data)

    def respond(self, data=None, error=None) -> dict:
        success = not error
        self.success = success
        self.data = data
        self.error = error
        if data is None and not error:
            raise ResponseError("Either data or error must be set")
        return dict(success=success, data=data, error=error)
