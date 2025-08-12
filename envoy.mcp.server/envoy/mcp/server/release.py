import base64
import collections
import hashlib
import json
import pathlib

import aiohttp
from gidgethub.aiohttp import GitHubAPI
from packaging.version import parse


ENVOY_RELEASES_URL = "https://github.com/envoyproxy/envoy/releases/download/v{version}/{asset}"


class ReleaseBinaryError(Exception):
    pass


class EnvoyRelease:
    @classmethod
    async def stable_versions(cls) -> dict:
        token = None
        async with aiohttp.ClientSession() as session:
            kwargs = {"oauth_token": token} if token else {}
            gh = GitHubAPI(session, "envoy-version-fetcher", **kwargs)
            version_content = await gh.getitem(
                "/repos/envoyproxy/envoy/contents/VERSION.txt"
            )

            version_txt = base64.b64decode(version_content["content"]).decode("utf-8").strip()
            current_dev_version = parse(version_txt.replace("-dev", ""))
            current_minor = current_dev_version.minor
            supported_minors = [current_minor - 1, current_minor - 2, current_minor - 3, current_minor - 4]
            version_info = collections.defaultdict(list)

            async for release in gh.getiter("/repos/envoyproxy/envoy/releases?per_page=100"):
                tag_name = release["tag_name"]
                if not tag_name.startswith('v'):
                    continue

                try:
                    version = parse(tag_name[1:])
                    if version.major == 1 and version.minor in supported_minors:
                        minor_key = f"1.{version.minor}"
                        version_info[minor_key].append({
                            "version": tag_name,
                            "patch": version.micro,
                            "date": release["published_at"],
                            "url": release["html_url"]
                        })
                except:
                    continue

            # Sort and organize the results
            supported_versions = {}
            for minor in sorted(supported_minors, reverse=True):
                minor_key = f"1.{minor}"
                if minor_key in version_info:
                    patches = sorted(
                        version_info[minor_key],
                        key=lambda x: x["patch"],
                        reverse=True)
                    supported_versions[minor_key] = patches

            return supported_versions

    def __init__(self, version: str) -> None:
        self.version = version

    async def download(self, binary: str, hash: str) -> pathlib.Path:
        binary_path = pathlib.Path("/tmp/envoy-bins") / self.version / binary
        url = ENVOY_RELEASES_URL.format(asset=binary, version=self.version)
        if not binary_path.exists():
            binary_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    with binary_path.open('wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

        sha = hashlib.sha256()
        with binary_path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha.update(byte_block)

        if sha.hexdigest() != hash:
            binary_path.unlink()
            raise ReleaseBinaryError(f"hash mismatch: {sha.hexdigest()} != {hash}")

        # chmod +x
        binary_path.chmod(binary_path.stat().st_mode | 0o111)
        return binary_path

    async def checksums(self) -> dict:
        url = ENVOY_RELEASES_URL.format(asset="checksums.txt.asc", version=self.version)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return self.parse_checksums(await response.text())

    def parse_checksums(self, content) -> dict:
        sections = content.split('\n\n')
        header = sections[0].split('\n')
        hash_type = header[1].split(': ')[1]

        file_hashes = {}
        for line in sections[1].split('\n'):
            if line.strip() and not line.startswith('-----'):
                hash_val, filepath = line.rsplit('  ', 1)
                if '/tmp/' in filepath:
                    filepath = filepath.split('/bin/', 1)[-1]
                file_hashes[filepath] = hash_val

        signature_start = content.index('-----BEGIN PGP SIGNATURE-----')
        signature_end = content.index('-----END PGP SIGNATURE-----') + len('-----END PGP SIGNATURE-----')
        signature_block = content[signature_start:signature_end]

        return {
            'hash_type': hash_type,
            'file_hashes': file_hashes,
            'signature_block': signature_block
        }
