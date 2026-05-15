"""Verify built wheels in dist/ have Requires-Dist matching setup.cfg.

Runs after `pants package ::` in CI. Walks dist/*.whl, parses METADATA,
locates the package's setup.cfg, and asserts:

    set(Requires-Dist without `; extra == ...`)
        == set(install_requires from setup.cfg)

Exits non-zero with a per-package diff on mismatch.
"""

import glob
import pathlib
import re
import sys
import zipfile
from collections import defaultdict
from email.parser import Parser

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def _norm(req_str: str) -> tuple[str, str]:
    r = Requirement(req_str)
    return canonicalize_name(r.name), str(r.specifier)


def _setup_cfg_install_requires(path: pathlib.Path) -> list[str]:
    reqs, in_options, in_ir = [], False, False
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            in_options = s == "[options]"
            in_ir = False
            continue
        if not in_options:
            continue
        if s.startswith("install_requires"):
            in_ir = True
            if "=" in raw:
                v = raw.split("=", 1)[1].strip()
                if v:
                    reqs.append(v)
            continue
        if in_ir:
            if raw and not raw[0].isspace():
                in_ir = False
                continue
            if s and not s.startswith("#"):
                reqs.append(s)
    return reqs


def _wheel_runtime_requires(whl: pathlib.Path) -> list[str]:
    with zipfile.ZipFile(whl) as zf:
        meta = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        msg = Parser().parsestr(zf.read(meta).decode())
    out = []
    for rd in msg.get_all("Requires-Dist") or []:
        if ";" in rd and "extra" in rd.split(";", 1)[1]:
            continue
        out.append(rd.split(";", 1)[0].strip())
    return out


def _pkg_name_from_wheel(whl: pathlib.Path) -> str:
    return whl.name.split("-")[0]


def _setup_cfg_for(dist_name: str) -> pathlib.Path | None:
    for cfg in pathlib.Path("py").glob("*/setup.cfg"):
        for line in cfg.read_text().splitlines():
            m = re.match(r"\s*name\s*=\s*(\S+)", line)
            if m and canonicalize_name(m.group(1)) == canonicalize_name(dist_name):
                return cfg
    return None


def main() -> int:
    failures: dict[str, list[str]] = defaultdict(list)
    wheels = sorted(
        p for p in pathlib.Path("dist").glob("*.whl"))
    if not wheels:
        print("ERROR: no wheels found in dist/", file=sys.stderr)
        return 2

    for whl in wheels:
        dist_name = _pkg_name_from_wheel(whl)
        cfg = _setup_cfg_for(dist_name)
        if cfg is None:
            failures[whl.name].append(
                f"no matching py/*/setup.cfg for dist name {dist_name!r}"
            )
            continue
        expected = {_norm(r) for r in _setup_cfg_install_requires(cfg)}
        actual = {_norm(r) for r in _wheel_runtime_requires(whl)}
        if expected == actual:
            print(f"OK  {whl.name}")
            continue
        extra = actual - expected
        missing = expected - actual
        if extra:
            failures[whl.name].append(
                f"unexpected Requires-Dist (leaked from pants/deps?): {sorted(extra)}"
            )
        if missing:
            failures[whl.name].append(
                f"missing Requires-Dist (in setup.cfg but not in wheel): {sorted(missing)}"
            )

    if failures:
        print("\nFAIL: wheel METADATA does not match setup.cfg", file=sys.stderr)
        for whl, errs in failures.items():
            print(f"  {whl}", file=sys.stderr)
            for e in errs:
                print(f"    - {e}", file=sys.stderr)
        return 1
    print(f"\nAll {len(wheels)} wheels match their setup.cfg install_requires.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
