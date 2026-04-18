"""差量计算：对比当前 manifest 与 export_base，生成 delta 信息"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from . import config
from .utils import log_info


def compute_delta(
    current: Dict[str, Dict[str, Any]],
    export_base: Dict[str, Dict[str, Any]],
    from_side: str,
    base_peer_token: str | None = None,
) -> Dict[str, Any]:
    """对比当前 manifest 与 export_base，生成 delta dict。

    返回即 delta.json 的内容，不含文件体。
    """
    changed: List[Dict[str, Any]] = []
    deleted: List[str] = []

    # 找新增 / 修改
    for path, info in current.items():
        if path not in export_base:
            changed.append(_entry(path, info))
        elif info["sha256"] != export_base[path].get("sha256"):
            changed.append(_entry(path, info))

    # 找删除
    for path in export_base:
        if path not in current:
            deleted.append(path)

    delta = {
        "packageId": uuid4().hex,
        "fromSide": from_side,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "basePeerToken": base_peer_token,
        "changed": changed,
        "deleted": deleted,
    }

    log_info(
        f"差量计算完成：changed={len(changed)}, deleted={len(deleted)}, "
        f"packageId={delta['packageId'][:8]}..."
    )
    return delta


def _entry(path: str, info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "path": path,
        "sha256": info["sha256"],
        "size": info["size"],
        "mtime": info.get("mtime", ""),
    }
