
from typing import Any, AsyncGenerator, Dict, Mapping, Tuple

import gidgethub.abc
import gidgethub.sansio

import abstracts

from aio.functional import async_property


class AGithubIterator(metaclass=abstracts.Abstraction):
    """Async iterator to wrap gidgethub API and provide `total_count`."""

    def __init__(
            self,
            api: gidgethub.abc.GitHubAPI,
            query: str,
            *args,
            **kwargs) -> None:
        self.api = api
        self.query = query
        self.args = args
        self.kwargs = kwargs
        self._inflate = kwargs.pop("inflate", None)

    async def __aiter__(self) -> AsyncGenerator[Any, None]:
        """Async iterate an API call, inflating the results."""
        aiter = self.api.getiter(
            self.query, *self.args, **self.kwargs)
        async for item in aiter:
            yield self.inflate(item)

    @property
    def count_request_headers(self) -> Dict[str, str]:
        """Request headers for API call to get `total_count`."""
        request_headers = gidgethub.sansio.create_headers(
            self.api.requester,
            accept=gidgethub.sansio.accept_format(),
            oauth_token=self.api.oauth_token)
        request_headers["content-length"] = "0"
        return request_headers

    @property
    def count_url(self) -> str:
        """Request URL for API call to get `total_count`."""
        return gidgethub.sansio.format_url(
            f"{self.query}&per_page=1",
            {},
            base_url=self.api.base_url)

    @async_property(cache=True)
    async def total_count(self) -> int:
        """Get `total_count` without iterating all items."""
        # https://github.com/brettcannon/gidgethub/discussions/153
        if self.api.rate_limit is not None:
            self.api.rate_limit.remaining -= 1
        return self.count_from_response(
            await self.api._request(
                "GET", self.count_url, self.count_request_headers, b''))

    def count_from_data(self, data: Dict) -> int:
        """Get `total_count` from the data."""
        return (
            int(data["total_count"])
            if "total_count" in data
            else 0)

    def count_from_headers(self, headers: Mapping[str, str]) -> int:
        """Get the last page link from from the headers resulting from the
        request for single page iteration."""
        return (
            int(headers["Link"].split(
                ",")[1].split(
                    ">")[0].split("=")[-1])
            if "Link" in headers
            else 0)

    def count_from_response(
            self,
            response: Tuple[int, Mapping[str, str], bytes]) -> int:
        """Get total count from the headers or data."""

        (data,
         self.api.rate_limit,
         more) = gidgethub.sansio.decipher_response(*response)

        return (
            self.count_from_headers(response[1])
            if "Link" in response[1]
            else self.count_from_data(data))

    def inflate(self, result: Any) -> Any:
        """Inflate a result."""
        return (
            self._inflate(result)
            if self._inflate
            else result)
