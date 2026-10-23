import argparse
import asyncio
import json
import pathlib
import re
import sys
from calendar import monthrange
from collections.abc import Iterable, Iterator
from datetime import datetime
from functools import cached_property

import aiohttp

from aio.run import runner

# TODO(phlax): Decide long-term home for this. Python drags a python toolchain into consumers' graphs (slow); consider reimplementing the NVD paging/backoff loop with curl + jq via the hermetic toolchains, or shipping as a prebuilt.

BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
PAGE_SIZE = 2000
MAX_CONCURRENCY = 4
MAX_RETRIES = 10
BACKOFF_BASE = 10


class NvdDownloaderError(Exception):
    pass


def date_month(value: str) -> datetime:
    """Parse YYYY-MM into the first day of that month."""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError(value)
        return datetime.strptime(value, "%Y-%m")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{value}'. Expected YYYY-MM (e.g. 2025-03).") from None


def date_months(value: str) -> set[str]:
    months = set(value.split(","))
    for month in months:
        date_month(month)
    return months


def next_month(value: datetime) -> datetime:
    if value.month == 12:
        return datetime(value.year + 1, 1, 1)
    return datetime(value.year, value.month + 1, 1)


def month_windows(
        start: datetime,
        end: datetime,
        skip: set[str] | None = None) -> Iterator[tuple[datetime, datetime]]:
    """Split an exclusive-end window into calendar months, omitting skipped months."""
    current = start
    while current < end:
        last_day = monthrange(current.year, current.month)[1]
        chunk_end = min(datetime(current.year, current.month, last_day, 23, 59, 59), end)
        if current.strftime("%Y-%m") not in (skip or set()):
            yield current, chunk_end
        current = next_month(current)


def nvd_url(start_date: datetime, end_date: datetime, start_index: int) -> str:
    return (
        f"{BASE_URL}?noRejected"
        f"&pubStartDate={start_date.strftime('%Y-%m-%dT%H:%M:%S.000')}"
        f"&pubEndDate={end_date.strftime('%Y-%m-%dT%H:%M:%S.999')}"
        f"&startIndex={start_index}&resultsPerPage={PAGE_SIZE}")


def ordered_pages(pages: Iterable[tuple[int, dict]]) -> list[dict]:
    return [page for _, page in sorted(pages, key=lambda item: item[0])]


def merge_pages(pages: Iterable[tuple[int, dict]]) -> dict:
    """Create one NVD document in offset order, retaining first-page metadata."""
    ordered = ordered_pages(pages)
    if not ordered:
        raise NvdDownloaderError("Cannot merge an empty set of NVD pages")
    vulnerabilities = [
        vulnerability
        for page in ordered
        for vulnerability in page.get("vulnerabilities", [])]
    return dict(
        ordered[0],
        startIndex=0,
        resultsPerPage=len(vulnerabilities),
        totalResults=len(vulnerabilities),
        vulnerabilities=vulnerabilities)


class NvdDownloader(runner.Runner):

    @property
    def end_date(self):
        return next_month(self.args.end)

    @cached_property
    def output_path(self) -> pathlib.Path | None:
        if not self.args.output_path:
            return None
        path = self.args.output_path.resolve()
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def overwrite(self):
        return self.args.overwrite

    @cached_property
    def semaphore(self):
        if self.args.max_concurrency < 1:
            raise NvdDownloaderError("--max_concurrency must be positive")
        return asyncio.Semaphore(self.args.max_concurrency)

    @property
    def skip(self) -> set[str]:
        return self.args.skip or set()

    @property
    def start_date(self):
        return self.args.start

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument("start", type=date_month, help="Start month (publication).")
        parser.add_argument("end", type=date_month, help="End month (publication), inclusive.")
        parser.add_argument(
            "--skip", type=date_months, help="Months to skip, comma separated in YYYY-MM format.")
        parser.add_argument(
            "--overwrite", action="store_true", help="Overwrite existing files.")
        parser.add_argument(
            "--output_path", type=pathlib.Path, help="Path to save downloaded JSON data.")
        parser.add_argument(
            "--max_concurrency", type=int, default=MAX_CONCURRENCY,
            help="Maximum concurrent requests.")

    async def fetch_page(self, session, start_date, end_date, start_index):
        url = nvd_url(start_date, end_date, start_index)
        self.log.debug(f"FETCH ({start_date:%Y-%m}): {start_index}\n  {url}")
        for attempt in range(1, MAX_RETRIES + 1):
            async with self.semaphore:
                async with session.get(url) as response:
                    if response.status != 429:
                        response.raise_for_status()
                        return start_date, end_date, start_index, await response.json()
            if attempt < MAX_RETRIES:
                wait_time = BACKOFF_BASE * attempt
                self.log.warning(
                    f"429 Too Many Requests ({start_date:%Y-%m}/{start_index}): "
                    f"attempt {attempt}/{MAX_RETRIES}, backing off {wait_time}s...")
                await asyncio.sleep(wait_time)
        raise NvdDownloaderError(
            f"NVD retries exhausted ({start_date:%Y-%m}/{start_index}) after {MAX_RETRIES} attempts")

    async def fetch_range(self, session, start_date, end_date):
        first = await self.fetch_page(session, start_date, end_date, 0)
        yield first
        total = first[3].get("totalResults", 0)
        page_size = first[3].get("resultsPerPage", PAGE_SIZE)
        if page_size < 1:
            if total:
                raise NvdDownloaderError("NVD returned a zero page size with nonzero totalResults")
            return
        tasks = [
            asyncio.create_task(self.fetch_page(session, start_date, end_date, offset))
            for offset in range(page_size, total, page_size)]
        try:
            for task in asyncio.as_completed(tasks):
                yield await task
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def fetch_window(self, start_date, end_date):
        async with aiohttp.ClientSession() as session:
            for start, end in month_windows(start_date, end_date, self.skip):
                async for data in self.fetch_range(session, start, end):
                    yield data

    def write_month(self, month: str, pages: list[tuple[int, dict]]) -> None:
        document = merge_pages(pages)
        if self.output_path is None:
            print(json.dumps(document))
            return
        output_file = self.output_path / f"{month}.json"
        try:
            with output_file.open("w" if self.overwrite else "x", encoding="utf-8") as stream:
                json.dump(document, stream)
        except FileExistsError:
            raise NvdDownloaderError(
                f"File {output_file} exists and overwrite was not specified") from None

    @runner.cleansup
    @runner.catches((NvdDownloaderError, aiohttp.ClientError))
    async def run(self):
        if self.start_date >= self.end_date:
            raise NvdDownloaderError("Start month must not be after end month")
        month = None
        pages = []
        async for start, end, offset, page in self.fetch_window(self.start_date, self.end_date):
            current_month = start.strftime("%Y-%m")
            if month is not None and current_month != month:
                self.write_month(month, pages)
                pages = []
            month = current_month
            self.log.info(
                f"RECV ({month}): {len(page.get('vulnerabilities', []))} at {offset}")
            pages.append((offset, page))
        if month is not None:
            self.write_month(month, pages)


def main(*args):
    return NvdDownloader(*args)()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
