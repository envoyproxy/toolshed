import argparse
import asyncio
import base64
import collections
import hashlib
import json
import os
import pathlib
import re
import signal
import sys
import tempfile
import time

import aiohttp
from gidgethub.aiohttp import GitHubAPI
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.prompts import base
from packaging.version import parse
import yaml

mcp = FastMCP("Envoy")

ENVOY_RELEASES_URL = "https://github.com/envoyproxy/envoy/releases/download/v{version}/{asset}"


# RESOURCES

@mcp.resource("envoy://release/{version}/{binary}:{hash}")
async def envoy_binary_resource(version: str,  binary: str, hash: str) -> str:
    """Envoy binary"""
    binary_path = pathlib.Path("/tmp/envoy-bins") / version / binary
    url = ENVOY_RELEASES_URL.format(asset=binary, version=version)
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
        return json.dumps({"ERROR": f"hash mismatch: {sha.hexdigest()} != {hash}"})

    # chmod +x
    binary_path.chmod(binary_path.stat().st_mode | 0o111)
    return json.dumps(dict(path=f"{binary_path}"))


@mcp.resource("envoy://checksum/{version}")
async def envoy_binary_checksums_resource(version: str) -> str:
    """Envoy release checksums"""
    envoy_release = EnvoyRelease(version)
    return await envoy_release.checksums()


@mcp.resource("envoy://versions/stable")
async def envoy_versions_resource() -> str:
    """Envoy versions"""
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
                patches = sorted(version_info[minor_key],
                               key=lambda x: x["patch"],
                               reverse=True)
                supported_versions[minor_key] = patches

        return supported_versions


@mcp.resource("envoy://ai/prompt")
async def envoy_prompt_resource() -> str:
    """Envoy binary"""
    current_file = pathlib.Path(__file__)
    context_file_path = current_file.parent / "prompt.txt"
    return context_file_path.read_text()


@mcp.resource("envoy://ai/context")
async def envoy_context_resource() -> str:
    """Envoy context
    """
    current_file = pathlib.Path(__file__)
    context_file_path = current_file.parent / "context.yaml"
    with context_file_path.open('r') as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


# TOOLS

@mcp.tool()
async def envoy_can_start(version: str, config_str: str, ctx: Context, wait: int = 2) -> str:
    """Start an envoy server, wait for some time to ensure it stays up, then kill it

    Args:
        config_str: Envoy configuration yaml as string
        version: Semantic version excluding any prefix
        wait: Wait time before killing the server (in seconds)
    """
    checksums = await ctx.read_resource(f"envoy://checksum/{version}")
    checksum = json.loads(checksums[0].content)["file_hashes"][f"envoy-{version}-linux-x86_64"]
    bin = await ctx.read_resource(f"envoy://release/{version}/envoy-{version}-linux-x86_64:{checksum}")
    binary = json.loads(bin[0].content)

    if "ERROR" in binary:
        return binary["ERROR"]

    config_path = pathlib.Path(tempfile.mkstemp(suffix=".yaml")[1])
    config_path.write_text(config_str)

    try:
        proc_id = f"can_start-{int(time.time())}"
        process_manager = ProcessManager()
        proc_data = await process_manager.start_envoy(config_str, proc_id)
        await asyncio.sleep(2)
        stdout_path = process_manager.registry_dir / f"{proc_id}.stdout.log"
        stderr_path = process_manager.registry_dir / f"{proc_id}.stderr.log"
        stdout = stderr = ""
        if stdout_path.exists():
            with open(stdout_path, 'rb') as f:
                stdout = f.read().decode()
            stdout_path.unlink(missing_ok=True)
        if stderr_path.exists():
            with open(stderr_path, 'rb') as f:
                stderr = f.read().decode()
            stderr_path.unlink(missing_ok=True)
        return_code = 0
    finally:
        return_code = json.loads(await process_manager.get_pid_data(proc_id)).get("exit_code", return_code)
        await process_manager.kill_process(proc_id)
        config_path.unlink()
    return json.dumps({"stdout": stdout, "stderr": stderr, "return_code": return_code})


@mcp.tool()
async def envoy_list_processes(ctx: Context = None) -> str:
    """List envoy server processes"""

    process_manager = ProcessManager()
    try:
        processes = await process_manager.list_processes()
        orphans = await process_manager.find_orphans()
        result = {
            "managed": processes,
            "orphans": orphans,
            "total_count": len(processes) + (len(orphans) if isinstance(orphans, list) else 0)
        }

        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def envoy_run(version: str, config_str: str, proc_id: str | None = None, ctx: Context = None) -> str:
    """Start an envoy server

    Args:
        config_str: Envoy configuration yaml as string
        proc_id: Process id, defaults to timestamp
        version: Semantic version excluding any prefix
    """
    checksums = await ctx.read_resource(f"envoy://checksum/{version}")
    checksum = json.loads(checksums[0].content)["file_hashes"][f"envoy-{version}-linux-x86_64"]
    bin = await ctx.read_resource(f"envoy://release/{version}/envoy-{version}-linux-x86_64:{checksum}")
    binary = json.loads(bin[0].content)
    if "ERROR" in binary:
        return json.dumps({"error": binary["ERROR"]})

    process_manager = ProcessManager()
    if proc_id is None:
        proc_id = f"{int(time.time())}"

    try:
        proc_data = await process_manager.start_envoy(config_str, proc_id)
        proc_data["binary_path"] = binary["path"]
        proc_data["version"] = version
        return json.dumps(proc_data)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def envoy_kill(proc_id: str = None, kill_all: bool = False, kill_orphans: bool = False, ctx: Context = None) -> str:
    """Kill an envoy process

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
        kill_all: Optionally kill all managed processes
        kill_orphans: Optionally kill all orphaned processes
    """
    process_manager = ProcessManager()
    results = []
    try:
        if not (kill_all or kill_orphans or proc_id):
            return json.dumps({"error": "Must specify proc_id, kill_all, or kill_orphans"})
        if id:
            results = [await process_manager.kill_process(proc_id)]
        else:
            if kill_all:
                results.extend(await process_manager.kill_all())
            if kill_orphans:
                results.extend(await process_manager.kill_orphans())
        return json.dumps({"killed": results})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def envoy_config_for(proc_id: str = None, ctx: Context = None) -> str:
    """Fetch config for a given server invokation

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
    """

    process_manager = ProcessManager()
    return await process_manager.get_config(proc_id)


@mcp.tool()
async def envoy_log_for(proc_id: str = None, ctx: Context = None) -> str:
    """Fetch log for a given server invokation

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
    """
    process_manager = ProcessManager()
    return await process_manager.get_log(proc_id)


@mcp.tool()
async def envoy_prune_procceses(ctx: Context = None) -> str:
    """Prune inactive process info
    """
    process_manager = ProcessManager()
    return await process_manager.prune_processes()


@mcp.tool()
async def envoy_context(ctx: Context) -> str:
    """Context for working with Envoy

    This MUST always be loaded when working with anything Envoy.
    """
    return await ctx.read_resource(f"envoy://ai/context")


@mcp.tool()
async def envoy_stable_versions(ctx: Context) -> str:
    """Check envoy stable versions"""
    return await ctx.read_resource(f"envoy://versions/stable")


# PROMPTS

@mcp.prompt()
def envoy_prompt() -> str:
    """Create an envoy prompt"""
    current_file = pathlib.Path(__file__)
    context_file_path = current_file.parent / "prompt.txt"
    return context_file_path.read_text()


# FUN

class ProcessManager:
    def __init__(self, registry_dir="/tmp/envoy_registry"):
        self.registry_dir = pathlib.Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True, parents=True)

    def _get_pid_file(self, proc_id):
        return self.registry_dir / f"{proc_id}.pid"

    def _hash_config(self, config_content):
        return hashlib.md5(config_content.encode()).hexdigest()

    async def get_config(self, proc_id):
        config_path = self.registry_dir / f"{proc_id}.yaml"
        return config_path.read_text()

    async def get_log(self, proc_id):
        log_path = self.registry_dir / f"{proc_id}.stderr.log"
        return log_path.read_text()

    async def get_pid_data(self, proc_id):
        log_path = self.registry_dir / f"{proc_id}.pid"
        return log_path.read_text()

    async def start_envoy(self, config_content, proc_id=None):
        if proc_id is None:
            proc_id = self._hash_config(config_content)
        config_path = self.registry_dir / f"{proc_id}.yaml"
        config_path.write_text(config_content)
        stdout_log_path = self.registry_dir / f"{proc_id}.stdout.log"
        stderr_log_path = self.registry_dir / f"{proc_id}.stderr.log"
        stdout_file = open(stdout_log_path, 'wb')
        stderr_file = open(stderr_log_path, 'wb')
        process = await asyncio.create_subprocess_exec(
            "envoy", "-c", str(config_path), "--disable-hot-restart",
            stdout=stdout_file,
            stderr=stderr_file,
            preexec_fn=os.setsid
        )
        pid_data = {
            "pid": process.pid,
            "proc_id": proc_id,
            "config_path": str(config_path),
            "start_time": time.time(),
            "stdout_path": str(stdout_log_path),
            "stderr_path": str(stderr_log_path)
        }

        with open(self._get_pid_file(proc_id), 'w') as f:
            json.dump(pid_data, f)
        asyncio.create_task(self._monitor_process_exit(process, proc_id, stdout_file, stderr_file))
        return pid_data

    async def _monitor_process_exit(self, process, proc_id, stdout_file, stderr_file):
        """Monitor process exit, close file handles, and update pid file"""
        await process.wait()
        stdout_file.close()
        stderr_file.close()
        with open(self._get_pid_file(proc_id), 'r') as f:
            pid_data = json.load(f)
        pid_data["end_time"] = time.time()
        pid_data["exit_code"] = process.returncode
        pid_data["active"] = False

        with open(self._get_pid_file(proc_id), 'w') as f:
            json.dump(pid_data, f)

    async def is_running(self, proc_id):
        pid_file = self._get_pid_file(proc_id)
        if not pid_file.exists():
            return False
        try:
            with open(pid_file, 'r') as f:
                pid_data = json.load(f)
            pid = pid_data["pid"]
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return False

    async def kill_process(self, proc_id):
        pid_file = self._get_pid_file(proc_id)
        if not pid_file.exists():
            return {"status": "not_found", "id": proc_id}
        try:
            with open(pid_file, 'r') as f:
                pid_data = json.load(f)
            pid = pid_data["pid"]
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    await asyncio.sleep(0.2)
                    try:
                        os.kill(pid, 0)
                    except OSError:
                        break
                else:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass
            except OSError:
                pass
            pid_file.unlink(missing_ok=True)
            if "config_path" in pid_data:
                config_path = pathlib.Path(pid_data["config_path"])
                if config_path.exists():
                    config_path.unlink()
            return {"status": "terminated", "id": proc_id}
        except (json.JSONDecodeError, KeyError):
            pid_file.unlink(missing_ok=True)
            return {"status": "error", "id": proc_id}

    async def list_processes(self):
        result = []
        for pid_file in self.registry_dir.glob("*.pid"):
            try:
                proc_id = pid_file.stem
                pid_data = json.loads(pid_file.read_text())
                is_active = await self.is_running(proc_id)
                pid_data["active"] = is_active
                result.append(pid_data)
            except Exception as e:
                continue
        return result

    async def prune_processes(self):
        result = []
        for pid_file in self.registry_dir.glob("*.pid"):
            try:
                proc_id = pid_file.stem
                with open(pid_file, 'r') as f:
                    pid_data = json.load(f)
                is_active = await self.is_running(proc_id)
                if not is_active:
                    pid_file.unlink()
                    log = self.registry_dir / f"{proc_id}.stderr.log"
                    if log.exists():
                        log.unlink()
                    config = self.registry_dir / f"{proc_id}.yaml"
                    if config.exists():
                        config.unlink()
            except Exception as e:
                continue
        return result

    async def kill_all(self):
        results = []
        processes = await self.list_processes()
        for proc in processes:
            if proc.get("active", False):
                results.append(await self.kill_process(proc["proc_id"]))
        return results

    async def running_processes(self):
            proc = await asyncio.create_subprocess_exec(
                "ps", "-eo", "pid,command",
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return stdout.decode().splitlines()

    async def find_orphans(self):
        try:
            envoy_procs = []
            for line in await self.running_processes():
                if "envoy" in line and "-c" in line and str(self.registry_dir) in line:
                    parts = line.strip().split()
                    if parts:
                        try:
                            pid = int(parts[0])
                            envoy_procs.append({
                                "pid": pid,
                                "command": " ".join(parts[1:])
                            })
                        except ValueError:
                            continue
            managed_pids = set()
            for proc in await self.list_processes():
                managed_pids.add(proc["pid"])
            orphans = [p for p in envoy_procs if p["pid"] not in managed_pids]
            return orphans
        except Exception as e:
            return {"error": str(e)}

    async def kill_orphans(self):
        orphans = await self.find_orphans()
        results = []
        if isinstance(orphans, dict) and "error" in orphans:
            return orphans
        for proc in orphans:
            try:
                pid = proc["pid"]
                os.kill(pid, signal.SIGTERM)
                await asyncio.sleep(1)
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                    results.append({"pid": pid, "status": "killed", "method": "SIGKILL"})
                except OSError:
                    results.append({"pid": pid, "status": "killed", "method": "SIGTERM"})
            except Exception as e:
                results.append({"pid": proc["pid"], "status": "error", "error": str(e)})
        return results


class EnvoyRelease:
    def __init__(self, version: str):
        self.version = version

    async def checksums(self):
        url = ENVOY_RELEASES_URL.format(asset="checksums.txt.asc", version=self.version)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return self.parse_checksums(await response.text())

    def parse_checksums(self, content):
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

        return json.dumps({
            'hash_type': hash_type,
            'file_hashes': file_hashes,
            'signature_block': signature_block
        })
