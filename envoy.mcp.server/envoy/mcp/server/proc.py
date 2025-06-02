import asyncio
import hashlib
import json
import os
import pathlib
import signal
import time

from envoy.mcp.server.errors import ProcessError


class ProcessManager:
    def __init__(self, registry_dir="/tmp/envoy_registry"):
        self.registry_dir = pathlib.Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True, parents=True)

    def _get_pid_file(self, proc_id) -> pathlib.Path:
        return self.registry_dir / f"{proc_id}.pid"

    def _hash_config(self, config_content):
        return hashlib.md5(config_content.encode()).hexdigest()

    async def get_config(self, proc_id):
        config_path = self.registry_dir / f"{proc_id}.yaml"
        if not config_path.exists():
            raise ProcessError(f"Config file does not exist: {config_path}")
        return config_path.read_text()

    async def get_log(self, proc_id):
        log_path = self.registry_dir / f"{proc_id}.stderr.log"
        if not log_path.exists():
            raise ProcessError(f"Log file does not exist: {log_path}")
        return log_path.read_text()

    async def get_pid_data(self, proc_id):
        log_path = self.registry_dir / f"{proc_id}.pid"
        return log_path.read_text()

    async def start_envoy(self, binary, config_content, proc_id=None):
        if proc_id is None:
            proc_id = self._hash_config(config_content)
        config_path = self.registry_dir / f"{proc_id}.yaml"
        config_path.write_text(config_content)
        stdout_log_path = self.registry_dir / f"{proc_id}.stdout.log"
        stderr_log_path = self.registry_dir / f"{proc_id}.stderr.log"
        stdout_file = stdout_log_path.open("wb")
        stderr_file = stderr_log_path.open("wb")
        process = await asyncio.create_subprocess_exec(
            binary, "-c", str(config_path), "--disable-hot-restart",
            stdout=stdout_file,
            stderr=stderr_file,
            preexec_fn=os.setsid)
        pid_data = {
            "pid": process.pid,
            "proc_id": proc_id,
            "config_path": str(config_path),
            "start_time": time.time(),
            "stdout_path": str(stdout_log_path),
            "stderr_path": str(stderr_log_path)
        }
        json.dump(
            pid_data,
            self._get_pid_file(proc_id).open('w'))
        asyncio.create_task(
            self._monitor_process_exit(
                process,
                proc_id,
                stdout_file,
                stderr_file))
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

    async def kill_orphans(self):
        import sys
        print(f"FIND ORPJANS", file=sys.stderr)
        orphans = await self.find_orphans()

        print(f"ORPJANS {orphans}", file=sys.stderr)


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
