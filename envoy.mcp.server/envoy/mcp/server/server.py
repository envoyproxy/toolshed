import argparse
import asyncio
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiohttp
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.prompts import base
import yaml

from envoy.mcp.server.errors import ProcessError
from envoy.mcp.server.proc import ProcessManager
from envoy.mcp.server.release import EnvoyRelease
from envoy.mcp.server.utils import ToolRequest


class ResourceError(Exception):
    pass


@dataclass
class AppContext:
    procs: ProcessManager

# TODO: re/move this once resource contexts are fixed
procs = ProcessManager()


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    try:
        yield AppContext(procs=procs)
    finally:
        pass


mcp = FastMCP("Envoy", lifespan=app_lifespan)


# RESOURCES

@mcp.resource("envoy://release/{version}/{binary}:{hash}", mime_type="application/json")
async def envoy_binary_resource(version: str,  binary: str, hash: str) -> dict:
    """Envoy binary"""
    # Handle ReleaseBinaryError
    return dict(path=f"{await EnvoyRelease(version).download(binary, hash)}")


@mcp.resource("envoy://checksum/{version}", mime_type="application/json")
async def envoy_checksums_resource(version: str) -> dict:
    """Envoy release checksums"""
    return await EnvoyRelease(version).checksums()


@mcp.resource("envoy://versions/{version_type}", mime_type="application/json")
async def envoy_versions_resource(version_type: str) -> dict:
    """Envoy versions"""
    if version_type == "stable":
        return await EnvoyRelease.stable_versions()
    raise ResourceError(f"Unrecognized version type: {version_type}")


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
async def envoy_context(ctx: Context) -> str:
    """Context for working with Envoy

    This MUST always be loaded when working with anything Envoy.
    """
    return await ctx.read_resource(f"envoy://ai/context")


@mcp.tool()
async def envoy_stable_versions(ctx: Context) -> dict:
    """Check envoy stable versions"""
    tool_request = ToolRequest(
        ctx,
        "event_stable_versions")
    async with tool_request as request:
        try:
            versions = await ctx.read_resource(f"envoy://versions/stable")
            return request.respond(data=json.loads(versions[0].content))
        except ValueError as e:
            return request.respond(error=str(e))


# Proxy tools

@mcp.tool()
async def envoy_proxy_can_start(version: str, config_str: str, ctx: Context, wait: int = 2) -> dict:
    """Start an envoy server, wait for some time to ensure it stays up, then kill it

    Args:
        config_str: Envoy configuration yaml as string
        version: Semantic version excluding any prefix
        wait: Wait time before killing the server (in seconds)
    """
    tool_request = ToolRequest(
        ctx,
        "event_proxy_can_start",
        version=version,
        config_str=config_str,
        wait=wait)
    async with tool_request as request:
        checksums = await ctx.read_resource(f"envoy://checksum/{version}")
        checksum = json.loads(checksums[0].content)["file_hashes"][f"envoy-{version}-linux-x86_64"]
        bin = await ctx.read_resource(f"envoy://release/{version}/envoy-{version}-linux-x86_64:{checksum}")
        binary = json.loads(bin[0].content)

        if "ERROR" in binary:
            return request.respond(error=binary["ERROR"])

        process_manager = ctx.request_context.lifespan_context.procs
        proc_id = f"can_start-{int(time.time())}"
        config_path = pathlib.Path(tempfile.mkstemp(suffix=".yaml")[1])
        config_path.write_text(config_str)
        stdout_path = process_manager.registry_dir / f"{proc_id}.stdout.log"
        stderr_path = process_manager.registry_dir / f"{proc_id}.stderr.log"
        try:
            proc_data = await process_manager.start_envoy(binary["path"], config_str, proc_id)
            await asyncio.sleep(2)
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
            if config_path.exists():
                config_path.unlink()
            if stdout_path.exists():
                stdout_path.unlink()
            if stderr_path.exists():
                stderr_path.unlink()
        error = (
            "Envoy did not start successfully"
            if (return_code != 0)
            else None)
        return request.respond(error=error, data={"stdout": stdout, "stderr": stderr, "return_code": return_code})


@mcp.tool()
async def envoy_proxy_config(ctx: Context, proc_id: str = None) -> str:
    """Fetch config for a given server invokation

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
    """

    tool_request = ToolRequest(
        ctx,
        "event_proxy_config")
    async with tool_request as request:
        process_manager = ctx.request_context.lifespan_context.procs
        try:
            return dict(data=await process_manager.get_config(proc_id))
        except ProcessError as e:
            return request.respond(error=str(e))


@mcp.tool()
async def envoy_proxy_kill(ctx: Context, proc_id: str = None, kill_all: bool = False, kill_orphans: bool = False) -> str:
    """Kill an envoy process or processes

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
        kill_all: Optionally kill all managed processes
        kill_orphans: Optionally kill all orphaned processes
    """
    tool_request = ToolRequest(
        ctx,
        "event_proxy_kill",
        proc_id=proc_id,
        kill_all=kill_all,
        kill_orphans=kill_orphans)
    async with tool_request as request:
        process_manager = ctx.request_context.lifespan_context.procs
        error = None
        data = []
        if proc_id:
            data = [await process_manager.kill_process(proc_id)]
        elif kill_all or kill_orphans:
            if kill_all:
                data.extend(await process_manager.kill_all())
            if kill_orphans:
                data.extend(await process_manager.kill_orphans())
        else:
            error = "Must specify proc_id, kill_all, or kill_orphans"
        return request.respond(data=data, error=error)


@mcp.tool()
async def envoy_proxy_list_processes(ctx: Context) -> str:
    """List envoy server processes"""
    tool_request = ToolRequest(
        ctx,
        "event_proxy_list_processes")
    async with tool_request as request:
        process_manager = ctx.request_context.lifespan_context.procs
        processes = await process_manager.list_processes()
        orphans = await process_manager.find_orphans()
        result = {
            "managed": processes,
            "orphans": orphans,
            "total_count": len(processes) + (len(orphans) if isinstance(orphans, list) else 0)
        }
        return request.respond(data=result)


@mcp.tool()
async def envoy_proxy_log(ctx: Context, proc_id: str) -> str:
    """Fetch log for a given server invokation

    Args:
        proc_id: Id for process, as provided by `envoy_list_processes`
    """
    tool_request = ToolRequest(
        ctx,
        "event_proxy_log")
    async with tool_request as request:
        process_manager = ctx.request_context.lifespan_context.procs
        try:
            return request.respond(data=await process_manager.get_log(proc_id))
        except ProcessError as e:
            return request.respond(error=str(e))


@mcp.tool()
async def envoy_proxy_prune_procceses(ctx: Context) -> str:
    """Prune inactive process info
    """
    tool_request = ToolRequest(
        ctx,
        "event_proxy_prune_processes")
    async with tool_request as request:
        process_manager = ctx.request_context.lifespan_context.procs
        return request.respond(data=await process_manager.prune_processes())


@mcp.tool()
async def envoy_proxy_run(ctx: Context, version: str, config_str: str, proc_id: str | None = None) -> str:
    """Start an envoy server

    Args:
        config_str: Envoy configuration yaml as string
        proc_id: Process id, defaults to timestamp
        version: Semantic version excluding any prefix
    """
    tool_request = ToolRequest(
        ctx,
        "event_proxy_run",
        version=version,
        config_str=config_str,
        proc_id=proc_id)
    async with tool_request as request:
        checksums = await ctx.read_resource(f"envoy://checksum/{version}")
        checksum = json.loads(checksums[0].content)["file_hashes"][f"envoy-{version}-linux-x86_64"]
        bin = await ctx.read_resource(f"envoy://release/{version}/envoy-{version}-linux-x86_64:{checksum}")
        binary = json.loads(bin[0].content)
        if "ERROR" in binary:
            return request.respond(error=binary["ERROR"])
        process_manager = ctx.request_context.lifespan_context.procs
        if proc_id is None:
            proc_id = f"{int(time.time())}"
        proc_data = await process_manager.start_envoy(binary["path"], config_str, proc_id)
        proc_data["binary_path"] = binary["path"]
        proc_data["version"] = version
        return request.respond(data=proc_data)


# PROMPTS

@mcp.prompt()
def envoy_prompt() -> str:
    """Create an envoy prompt"""
    current_file = pathlib.Path(__file__)
    context_file_path = current_file.parent / "prompt.txt"
    return context_file_path.read_text()
