import io
import json
import pathlib
import tempfile
import unittest
import zipfile

try:
    from dependency.cve import cvelist_fetch
except ModuleNotFoundError as error:
    if error.name != "dependency":
        raise
    import cvelist_fetch


def record(
        cve_id, published, affected, state="PUBLISHED", adp=None, metrics=None,
        descriptions=None):
    cna = {"affected": affected}
    if metrics is not None:
        cna["metrics"] = metrics
    if descriptions is not None:
        cna["descriptions"] = descriptions
    containers = {"cna": cna}
    if adp is not None:
        containers["adp"] = adp
    return {
        "cveMetadata": {
            "cveId": cve_id,
            "state": state,
            "assignerShortName": "example",
            "datePublished": published,
            "dateUpdated": published,
        },
        "containers": containers,
    }


def nested_archive(path: pathlib.Path, records: dict[str, dict]) -> pathlib.Path:
    """A release-style archive: a zip holding `cves.zip` holding `cves/YYYY/Nxxx/CVE-*.json`."""
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zipped:
        zipped.writestr("cves/", "")
        for name, data in records.items():
            zipped.writestr(name, json.dumps(data))
    with zipfile.ZipFile(path, "w") as outer:
        outer.writestr("cves.zip", inner.getvalue())
    return path


class RecordTest(unittest.TestCase):

    def test_record_year(self):
        self.assertEqual(cvelist_fetch.record_year("cves/2024/1xxx/CVE-2024-1234.json"), 2024)
        for name in (
                "cves/2024/1xxx/", "cves/2024/", "cves/delta.json", "cves/xxxx/1xxx/CVE-1.json",
                "other/2024/1xxx/CVE-2024-1234.json", "cves/2024/1xxx/CVE-2024-1234.txt"):
            with self.subTest(name=name):
                self.assertIsNone(cvelist_fetch.record_year(name))

    def test_compact(self):
        compacted = cvelist_fetch.compact(
            record(
                "CVE-2024-0001",
                "2024-01-15T00:00:00.000Z",
                [{"vendor": "example", "product": "widget",
                  "versions": [{"version": "< 2.0", "status": "affected"}]}],
                adp=[{
                    "providerMetadata": {"shortName": "CISA-ADP"},
                    "affected": [{"cpes": ["cpe:2.3:a:example:widget:*:*:*:*:*:*:*:*"]}],
                    "metrics": [{
                        "cvssV3_1": {
                            "baseSeverity": "HIGH",
                            "baseScore": 7.5,
                            "vectorString": "x"}}],
                }],
                metrics=[
                    {"other": {"type": "ssvc", "content": {}}},
                    {"cvssV4_0": {"baseSeverity": "LOW", "baseScore": 2.0},
                     "format": "CVSS"}],
                descriptions=[
                    {"lang": "es", "value": "hola"},
                    {"lang": "en-US", "value": "hello"}]))
        self.assertEqual(
            compacted,
            {
                "id": "CVE-2024-0001",
                "state": "PUBLISHED",
                "assigner": "example",
                "published": "2024-01-15T00:00:00.000Z",
                "updated": "2024-01-15T00:00:00.000Z",
                "descriptions": [{"lang": "en-US", "value": "hello"}],
                "metrics": [
                    {"cvssV4_0": {"baseSeverity": "LOW", "baseScore": 2.0}},
                    {"cvssV3_1": {"baseSeverity": "HIGH", "baseScore": 7.5}}],
                "affected": [
                    {"vendor": "example", "product": "widget",
                     "versions": [{"version": "< 2.0", "status": "affected"}],
                     "provider": "cna"},
                    {"cpes": ["cpe:2.3:a:example:widget:*:*:*:*:*:*:*:*"],
                     "provider": "CISA-ADP"}],
            })

    def test_compact_skips_unusable(self):
        self.assertIsNone(
            cvelist_fetch.compact(
                record("CVE-2024-0002", "2024-01-15T00:00:00.000Z", [], state="REJECTED")))
        self.assertIsNone(
            cvelist_fetch.compact(record("CVE-2024-0003", "2024-01-15T00:00:00.000Z", [])))
        self.assertIsNone(cvelist_fetch.compact({}))

    def test_compact_descriptions_fallback(self):
        self.assertEqual(
            cvelist_fetch.compact_descriptions(
                [{"lang": "fr", "value": "a"}, {"lang": "de", "value": "b"}]),
            [{"lang": "fr", "value": "a"}])
        self.assertEqual(cvelist_fetch.compact_descriptions([]), [])

    def test_record_month(self):
        for published, expected in (
                ("2024-03-05T00:00:00Z", "2024-03"),
                ("2024-03-05T00:00:00.123", "2024-03"),
                ("2024-03-05T00:00:00.123+00:00", "2024-03"),
                ("2023-12-31T23:30:00-02:00", "2024-01"),
                ("2024-01-01T01:30:00+05:30", "2023-12"),
                ("2024-03", "2024-03")):
            with self.subTest(published=published):
                self.assertEqual(
                    cvelist_fetch.record_month({"published": published}, 2024), expected)
        self.assertEqual(cvelist_fetch.record_month({"published": None}, 2023), "2023-01")


class ExtractTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = pathlib.Path(self.tempdir.name)
        affected = [{
            "vendor": "example",
            "product": "widget",
            "versions": [{"version": "1", "status": "affected"}]}]

        def published(cve_id, date, **kwargs):
            return record(cve_id, f"{date}T00:00:00Z", affected, **kwargs)

        self.archive = nested_archive(
            self.path / "release.zip",
            {
                "cves/2023/1xxx/CVE-2023-1000.json": published("CVE-2023-1000", "2023-05-01"),
                "cves/2023/1xxx/CVE-2023-1001.json": published("CVE-2023-1001", "2024-03-01"),
                "cves/2024/9xxx/CVE-2024-9000.json": published(
                    "CVE-2024-9000", "2023-12-31"),
                "cves/2023/9xxx/CVE-2023-9001.json": record(
                    "CVE-2023-9001", "2023-12-31T23:30:00-02:00", affected),
                "cves/2024/1xxx/CVE-2024-1000.json": published("CVE-2024-1000", "2024-01-20"),
                "cves/2024/1xxx/CVE-2024-1001.json": published("CVE-2024-1001", "2024-01-21"),
                "cves/2024/2xxx/CVE-2024-2000.json": published("CVE-2024-2000", "2024-02-01"),
                "cves/2024/2xxx/CVE-2024-2001.json": record(
                    "CVE-2024-2001", "2024-02-02T00:00:00Z", [], state="REJECTED"),
                "cves/2025/1xxx/CVE-2025-1000.json": published("CVE-2025-1000", "2025-01-01"),
                "cves/delta.json": {"not": "a record"},
            })

    def downloader(self, *args):
        return cvelist_fetch.CvelistDownloader(
            "2024", f"--output_path={self.path / 'out'}", f"--archive={self.archive}", *args)

    def test_inner_archive(self):
        inner = cvelist_fetch.inner_archive(self.archive, self.path / "extract")
        self.assertEqual(inner.name, "cves.zip")
        with zipfile.ZipFile(inner) as zipped:
            self.assertIn("cves/2024/1xxx/CVE-2024-1000.json", zipped.namelist())

    def test_inner_archive_requires_single_zip(self):
        bad = self.path / "bad.zip"
        with zipfile.ZipFile(bad, "w") as outer:
            outer.writestr("a.zip", "")
            outer.writestr("b.zip", "")
        with self.assertRaises(cvelist_fetch.CvelistDownloaderError):
            cvelist_fetch.inner_archive(bad, self.path / "extract")

    def test_extract(self):
        downloader = self.downloader()
        inner = cvelist_fetch.inner_archive(self.archive, self.path / "extract")
        (self.path / "out").mkdir()
        (self.path / "out" / "2020-01.json").write_text("stale")
        counts = downloader.extract(inner)
        self.assertEqual(counts, {"2024-01": 3, "2024-02": 1, "2024-03": 1, "2025-01": 1})
        self.assertEqual(
            sorted(p.name for p in (self.path / "out").glob("*.json")),
            ["2024-01.json", "2024-02.json", "2024-03.json", "2025-01.json"])
        with (self.path / "out" / "2024-03.json").open() as stream:
            self.assertEqual(
                [r["id"] for r in json.load(stream)["records"]], ["CVE-2023-1001"])
        with (self.path / "out" / "2024-01.json").open() as stream:
            documents = [
                json.loads(line)
                for line in stream.read().replace("}{", "}\n{").splitlines()]
        self.assertEqual(
            [r["id"] for document in documents for r in document["records"]],
            ["CVE-2023-9001", "CVE-2024-1000", "CVE-2024-1001"])
        self.assertEqual(documents[0]["records"][0]["affected"][0]["provider"], "cna")

    def test_extract_chunks(self):
        downloader = self.downloader()
        inner = cvelist_fetch.inner_archive(self.archive, self.path / "extract")
        original = cvelist_fetch.CHUNK_SIZE
        cvelist_fetch.CHUNK_SIZE = 1
        self.addCleanup(setattr, cvelist_fetch, "CHUNK_SIZE", original)
        downloader.extract(inner)
        text = (self.path / "out" / "2024-01.json").read_text()
        self.assertEqual(text.count('{"records": ['), 3)

    def test_run(self):
        self.assertFalse(self.downloader()())
        self.assertTrue((self.path / "out" / "2024-01.json").exists())
        self.assertFalse((self.path / "out" / "2023-05.json").exists())
        self.assertFalse((self.path / "out" / "2023-12.json").exists())


if __name__ == "__main__":
    unittest.main()
