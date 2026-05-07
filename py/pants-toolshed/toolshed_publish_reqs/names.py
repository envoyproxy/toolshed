import re

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def _publish_req_target_name(req_str: str) -> str:
    canonical = canonicalize_name(Requirement(req_str).name).replace("-", "_")
    sanitized = re.sub(r"[^a-z0-9_]", "_", canonical)
    collapsed = re.sub(r"_+", "_", sanitized)
    return f"_publish__{collapsed}"
