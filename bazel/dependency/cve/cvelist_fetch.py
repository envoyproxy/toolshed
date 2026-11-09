import json
import os
import pathlib
import sys
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from functools import cached_property

import aiohttp

from aio.run import runner

# The CVE Program publishes the full cvelistV5 corpus as a (nested) zip with
# each release. The CNA/ADP asserted `affected` data in these records is
# available on publication, unlike NVD CPE configurations, which are only
# added if/when NVD analyzes a CVE.
RELEASES_URL = "https://api.github.com/repos/CVEProject/cvelistV5/releases/latest"
ASSET_SUFFIX = "_all_CVEs_at_midnight.zip.zip"
CHUNK_SIZE = 2000
DOWNLOAD_CHUNK_SIZE = 1 << 20


class CvelistDownloaderError(Exception):
    pass


def record_year(name: str) -> int | None:
    """Identifier year from an archive member name (`cves/YYYY/Nxxx/CVE-YYYY-N.json`).

    This is the year the id was assigned, not necessarily the publication year.
    """
    parts = name.split("/")
    if len(parts) != 4 or parts[0] != "cves" or not parts[3].endswith(".json"):
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def compact_descriptions(descriptions: list) -> list:
    """The (first) english description, falling back to whatever is there."""
    english = [d for d in descriptions if str(d.get("lang", "")).lower().startswith("en")]
    return (english or descriptions)[:1]


def compact_metrics(metrics: list) -> list:
    """Only the cvss scores, dropping ssvc/kev/etc `other` entries."""
    return [{
        k: {
            "baseSeverity": v.get("baseSeverity"),
            "baseScore": v.get("baseScore")}
        for k, v in metric.items()
        if k.startswith("cvss") and isinstance(v, dict)}
            for metric in metrics
            if any(k.startswith("cvss") for k in metric)]


def compact(record: dict) -> dict | None:
    """Minimal representation of a CVE record for matching, or None if unusable."""
    meta = record.get("cveMetadata", {})
    if meta.get("state") != "PUBLISHED":
        return None
    containers = record.get("containers", {})
    cna = containers.get("cna", {})
    affected = [dict(item, provider="cna") for item in cna.get("affected", [])]
    metrics = list(cna.get("metrics", []))
    for adp in containers.get("adp", []):
        provider = adp.get("providerMetadata", {}).get("shortName", "adp")
        affected.extend(dict(item, provider=provider) for item in adp.get("affected", []))
        metrics.extend(adp.get("metrics", []))
    if not affected:
        return None
    return {
        "id": meta["cveId"],
        "state": meta["state"],
        "assigner": meta.get("assignerShortName"),
        "published": meta.get("datePublished"),
        "updated": meta.get("dateUpdated"),
        "descriptions": compact_descriptions(cna.get("descriptions", [])),
        "metrics": compact_metrics(metrics),
        "affected": affected,
    }


def record_month(record: dict, year: int) -> str:
    """UTC publication month (`YYYY-MM`), falling back to the identifier year.

    Timestamps may carry a `Z` or an offset; the month is taken in UTC, as the
    scanner normalizes publication dates.
    """
    published = record.get("published")
    if not published:
        return f"{year}-01"
    try:
        parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        return published[:7]
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m")


def inner_archive(outer: pathlib.Path, tempdir: pathlib.Path) -> pathlib.Path:
    """Extract the single nested zip of json records from the release asset."""
    with zipfile.ZipFile(outer) as archive:
        names = [name for name in archive.namelist() if name.endswith(".zip")]
        if len(names) != 1:
            raise CvelistDownloaderError(f"Expected a single nested zip, found: {names}")
        return pathlib.Path(archive.extract(names[0], tempdir))


class CvelistDownloader(runner.Runner):

    @property
    def archive(self) -> pathlib.Path | None:
        return self.args.archive

    @cached_property
    def output_path(self) -> pathlib.Path:
        path = self.args.output_path.resolve()
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def start_year(self) -> int:
        return self.args.start_year

    @property
    def github_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument("start_year", type=int, help="First publication year to keep.")
        parser.add_argument(
            "--output_path", type=pathlib.Path, required=True, help="Path to save JSON data.")
        parser.add_argument(
            "--archive",
            type=pathlib.Path,
            help="Use a previously downloaded release archive rather than downloading.")

    async def asset_url(self, session) -> str:
        async with session.get(RELEASES_URL, headers=self.github_headers) as response:
            response.raise_for_status()
            release = await response.json()
        for asset in release.get("assets", []):
            if asset["name"].endswith(ASSET_SUFFIX):
                self.log.info(f"RELEASE: {release.get('tag_name')} ({asset['name']})")
                return asset["browser_download_url"]
        raise CvelistDownloaderError(
            f"No {ASSET_SUFFIX} asset found in release {release.get('tag_name')}")

    async def download(self, path: pathlib.Path) -> pathlib.Path:
        async with aiohttp.ClientSession() as session:
            url = await self.asset_url(session)
            self.log.info(f"FETCH: {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                with path.open("wb") as stream:
                    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                        stream.write(chunk)
        return path

    def write_chunk(self, month: str, records: list) -> None:
        with (self.output_path / f"{month}.json").open("a", encoding="utf-8") as stream:
            json.dump({"records": records}, stream)

    def extract(self, archive: pathlib.Path) -> dict[str, int]:
        """Write compacted records published from `start_year` to `YYYY-MM.json` month files.

        Each month file holds consecutive `{"records": [...]}` objects, as the
        NVD month files hold consecutive page objects. The cutoff applies to
        the publication date: an id assigned in an earlier year may be
        published later.
        """
        for existing in self.output_path.glob("*.json"):
            existing.unlink()
        months = defaultdict(list)
        counts = defaultdict(int)
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                year = record_year(info.filename)
                if year is None:
                    continue
                with zipped.open(info) as stream:
                    record = compact(json.load(stream))
                if not record:
                    continue
                month = record_month(record, year)
                if int(month[:4]) < self.start_year:
                    continue
                months[month].append(record)
                counts[month] += 1
                if len(months[month]) >= CHUNK_SIZE:
                    self.write_chunk(month, months.pop(month))
        for month, records in months.items():
            self.write_chunk(month, records)
        for month in sorted(counts):
            self.log.info(f"WRITE ({month}): {counts[month]}")
        return dict(counts)

    @runner.cleansup
    @runner.catches((CvelistDownloaderError, aiohttp.ClientError, zipfile.BadZipFile))
    async def run(self):
        tempdir = pathlib.Path(self.tempdir.name)
        outer = self.archive or await self.download(tempdir / "cvelist.zip")
        self.extract(inner_archive(outer, tempdir))


def main(*args):
    return CvelistDownloader(*args)()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
