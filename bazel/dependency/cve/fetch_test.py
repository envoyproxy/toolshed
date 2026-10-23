import argparse
import asyncio
import io
import json
import pathlib
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from datetime import datetime
from unittest.mock import AsyncMock, Mock, mock_open, patch

import aiohttp

try:
    from dependency.cve import fetch
except ModuleNotFoundError as error:
    if error.name != "dependency":
        raise
    import fetch


class DateTest(unittest.TestCase):

    def test_date_month(self):
        self.assertEqual(fetch.date_month("2024-02"), datetime(2024, 2, 1))

    def test_invalid_date_month(self):
        for value in ("2024", "2024-2", "2024-13", "0000-01", "2024-02-01", ""):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                fetch.date_month(value)

    def test_date_months(self):
        self.assertEqual(
            fetch.date_months("2024-02,2024-12,2024-02"), {"2024-02", "2024-12"})
        for value in ("2024-01,", "invalid"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                fetch.date_months(value)

    def test_december_rollover(self):
        self.assertEqual(fetch.next_month(datetime(2024, 12, 1)), datetime(2025, 1, 1))
        downloader = fetch.NvdDownloader("2024-12", "2024-12")
        self.assertEqual(downloader.end_date, datetime(2025, 1, 1))

    def test_month_windows(self):
        self.assertEqual(
            list(fetch.month_windows(datetime(2024, 12, 1), datetime(2025, 2, 1))),
            [(datetime(2024, 12, 1), datetime(2024, 12, 31, 23, 59, 59)),
             (datetime(2025, 1, 1), datetime(2025, 1, 31, 23, 59, 59))])

    def test_leap_year_and_partial_window(self):
        self.assertEqual(
            list(fetch.month_windows(datetime(2024, 2, 1), datetime(2024, 3, 1))),
            [(datetime(2024, 2, 1), datetime(2024, 2, 29, 23, 59, 59))])
        self.assertEqual(
            list(fetch.month_windows(datetime(2024, 2, 5), datetime(2024, 2, 10))),
            [(datetime(2024, 2, 5), datetime(2024, 2, 10))])

    def test_skip_including_december(self):
        self.assertEqual(
            list(fetch.month_windows(
                datetime(2024, 12, 1), datetime(2025, 2, 1), {"2024-12"})),
            [(datetime(2025, 1, 1), datetime(2025, 1, 31, 23, 59, 59))])
        self.assertEqual(
            list(fetch.month_windows(
                datetime(2024, 12, 1), datetime(2025, 1, 1), {"2024-12"})), [])

    def test_empty_window(self):
        self.assertEqual(
            list(fetch.month_windows(datetime(2024, 1, 1), datetime(2024, 1, 1))), [])

    def test_nvd_url(self):
        self.assertEqual(
            fetch.nvd_url(datetime(2024, 2, 1), datetime(2024, 2, 29, 23, 59, 59), 4000),
            "https://services.nvd.nist.gov/rest/json/cves/2.0?noRejected"
            "&pubStartDate=2024-02-01T00:00:00.000"
            "&pubEndDate=2024-02-29T23:59:59.999"
            "&startIndex=4000&resultsPerPage=2000")


class OutputTest(unittest.TestCase):

    def setUp(self):
        self.first = {
            "format": "NVD_CVE", "version": "2.0", "timestamp": "2024-02-01T00:00:00",
            "startIndex": 0, "resultsPerPage": 1, "totalResults": 3,
            "vulnerabilities": [{"cve": {"id": "CVE-first"}}]}
        self.pages = [
            (10, {"startIndex": 10, "vulnerabilities": [{"cve": {"id": "CVE-last"}}]}),
            (2, {"startIndex": 2, "vulnerabilities": [{"cve": {"id": "CVE-middle"}}]}),
            (0, self.first)]
        self.downloader = fetch.NvdDownloader("2024-02", "2024-02")

    def test_ordering_and_merge(self):
        self.assertEqual(
            [page["startIndex"] for page in fetch.ordered_pages(self.pages)], [0, 2, 10])
        document = fetch.merge_pages(self.pages)
        self.assertEqual(
            [v["cve"]["id"] for v in document["vulnerabilities"]],
            ["CVE-first", "CVE-middle", "CVE-last"])
        self.assertEqual(document["format"], "NVD_CVE")
        self.assertEqual(document["version"], "2.0")
        self.assertEqual(document["timestamp"], self.first["timestamp"])
        self.assertEqual(document["startIndex"], 0)
        self.assertEqual(document["resultsPerPage"], 3)
        self.assertEqual(document["totalResults"], 3)
        self.assertEqual(len(self.first["vulnerabilities"]), 1)

    def test_empty_pages(self):
        with self.assertRaises(fetch.NvdDownloaderError):
            fetch.merge_pages([])
        self.assertEqual(
            fetch.merge_pages([(0, {"totalResults": 0, "vulnerabilities": []})]),
            {"totalResults": 0, "resultsPerPage": 0, "startIndex": 0, "vulnerabilities": []})

    def test_stdout_is_one_document(self):
        with redirect_stdout(io.StringIO()) as output:
            self.downloader.write_month("2024-02", self.pages)
        self.assertEqual(json.loads(output.getvalue()), fetch.merge_pages(self.pages))

    def test_output_file_and_overwrite(self):
        self.downloader.__dict__["output_path"] = pathlib.Path("output")
        for overwrite, mode in ((False, "x"), (True, "w")):
            self.downloader.args.overwrite = overwrite
            with self.subTest(overwrite=overwrite), patch.object(
                    pathlib.Path, "open", mock_open()) as opened:
                self.downloader.write_month("2024-02", self.pages)
                opened.assert_called_once_with(mode, encoding="utf-8")
                content = "".join(call.args[0] for call in opened().write.call_args_list)
                self.assertEqual(json.loads(content), fetch.merge_pages(self.pages))

    def test_existing_file_is_not_overwritten(self):
        self.downloader.__dict__["output_path"] = pathlib.Path("output")
        with patch.object(pathlib.Path, "open", side_effect=FileExistsError):
            with self.assertRaisesRegex(fetch.NvdDownloaderError, "overwrite was not specified"):
                self.downloader.write_month("2024-02", self.pages)


class DownloaderTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.downloader = fetch.NvdDownloader("2024-12", "2025-01", "--max_concurrency", "2")
        self.downloader.__dict__["log"] = Mock()
        self.start = datetime(2024, 12, 1)
        self.end = datetime(2024, 12, 31, 23, 59, 59)

    def session(self, status=200, document=None):
        response = Mock(status=status)
        response.json = AsyncMock(return_value=document or {"totalResults": 0})
        context = AsyncMock()
        context.__aenter__.return_value = response
        return Mock(get=Mock(return_value=context)), response

    async def test_fetch_page(self):
        session, response = self.session(document={"totalResults": 1})
        result = await self.downloader.fetch_page(session, self.start, self.end, 0)
        self.assertEqual(result, (self.start, self.end, 0, {"totalResults": 1}))
        response.raise_for_status.assert_called_once()
        session.get.assert_called_once_with(fetch.nvd_url(self.start, self.end, 0))

    async def test_shared_semaphore_limits_requests(self):
        self.assertIs(self.downloader.semaphore, self.downloader.semaphore)
        active = 0
        peak = 0

        @asynccontextmanager
        async def get(url):
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            try:
                await asyncio.sleep(0.001)
                yield self.session()[1]
            finally:
                active -= 1

        session = Mock(get=get)
        await asyncio.gather(*(
            self.downloader.fetch_page(session, self.start, self.end, offset)
            for offset in range(8)))
        self.assertEqual(peak, 2)

    async def test_invalid_concurrency(self):
        for value in ("0", "-1"):
            downloader = fetch.NvdDownloader("2024-12", "2024-12", "--max_concurrency", value)
            with self.subTest(value=value), self.assertRaises(fetch.NvdDownloaderError):
                _ = downloader.semaphore

    async def test_exhausted_retries_release_semaphore_before_backoff(self):
        session, _ = self.session(status=429)

        async def sleep(delay):
            self.assertEqual(self.downloader.semaphore._value, 2)

        with patch.object(fetch, "MAX_RETRIES", 3), patch.object(
                fetch.asyncio, "sleep", AsyncMock(side_effect=sleep)) as backoff:
            with self.assertRaisesRegex(fetch.NvdDownloaderError, "retries exhausted"):
                await self.downloader.fetch_page(session, self.start, self.end, 0)
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual([call.args[0] for call in backoff.await_args_list], [10, 20])

    async def test_retry_then_success(self):
        limited, _ = self.session(status=429)
        success, _ = self.session(document={"totalResults": 1})
        session = Mock(get=Mock(side_effect=[limited.get(), success.get()]))
        with patch.object(fetch.asyncio, "sleep", AsyncMock()) as backoff:
            result = await self.downloader.fetch_page(session, self.start, self.end, 0)
        self.assertEqual(result[3], {"totalResults": 1})
        backoff.assert_awaited_once_with(fetch.BACKOFF_BASE)

    async def test_non_rate_limit_errors_propagate(self):
        session, response = self.session(status=500)
        response.raise_for_status.side_effect = aiohttp.ClientError("HTTP 500")
        with self.assertRaises(aiohttp.ClientError):
            await self.downloader.fetch_page(session, self.start, self.end, 0)
        self.assertEqual(session.get.call_count, 1)

    async def test_paging_uses_reported_page_size(self):
        async def page(session, start, end, offset):
            if offset == 2:
                await asyncio.sleep(0.01)
            return start, end, offset, {
                "totalResults": 5, "resultsPerPage": 2, "startIndex": offset,
                "vulnerabilities": [offset]}

        self.downloader.fetch_page = AsyncMock(side_effect=page)
        results = [
            result async for result in self.downloader.fetch_range(Mock(), self.start, self.end)]
        self.assertEqual([result[2] for result in results], [0, 4, 2])
        self.assertEqual(
            fetch.merge_pages((result[2], result[3]) for result in results)["vulnerabilities"],
            [0, 2, 4])

    async def test_empty_range(self):
        self.downloader.fetch_page = AsyncMock(
            return_value=(self.start, self.end, 0, {"totalResults": 0, "resultsPerPage": 0}))
        results = [
            result async for result in self.downloader.fetch_range(Mock(), self.start, self.end)]
        self.assertEqual(len(results), 1)
        self.downloader.fetch_page.assert_awaited_once()

    async def test_invalid_page_size(self):
        self.downloader.fetch_page = AsyncMock(
            return_value=(self.start, self.end, 0, {"totalResults": 2, "resultsPerPage": 0}))
        with self.assertRaises(fetch.NvdDownloaderError):
            _ = [
                result async for result in self.downloader.fetch_range(
                    Mock(), self.start, self.end)]

    async def test_fetch_window_skips_months(self):
        self.downloader.args.skip = {"2024-12"}
        called = []

        async def fetch_range(session, start, end):
            called.append((start, end))
            yield start, end, 0, {}

        self.downloader.fetch_range = fetch_range
        with patch.object(fetch.aiohttp, "ClientSession", return_value=AsyncMock()):
            results = [
                result async for result in self.downloader.fetch_window(
                    self.start, datetime(2025, 2, 1))]
        self.assertEqual(len(results), 1)
        self.assertEqual(called, [(datetime(2025, 1, 1), datetime(2025, 1, 31, 23, 59, 59))])

    async def test_run_flushes_months_and_orders_output(self):
        async def window(start, end):
            yield self.start, self.end, 2, {"vulnerabilities": [2]}
            yield self.start, self.end, 0, {"vulnerabilities": [0]}
            yield datetime(2025, 1, 1), datetime(2025, 1, 31), 0, {"vulnerabilities": [3]}

        self.downloader.fetch_window = window
        self.downloader.cleanup = AsyncMock()
        with redirect_stdout(io.StringIO()) as output:
            await self.downloader.run()
        self.assertEqual(
            [json.loads(line)["vulnerabilities"] for line in output.getvalue().splitlines()],
            [[0, 2], [3]])
        self.downloader.cleanup.assert_awaited_once()

    async def test_reversed_window_exits_with_error(self):
        self.downloader.args.start = datetime(2025, 2, 1)
        self.downloader.cleanup = AsyncMock()
        self.assertEqual(await self.downloader.run(), 1)
        self.downloader.log.error.assert_called_once()
        self.downloader.cleanup.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
