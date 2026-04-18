"""导出流程：delta + changed files → zip → base64 → 分片写入 .sync/out/"""

import base64
import io
import json
import zipfile
from pathlib import Path
from typing import Dict, Any

from . import config
from .scanner import _get_main_dir
from .utils import log_info, log_warn


def export_package(
    vault_root: Path,
    delta: Dict[str, Any],
    current_manifest: Dict[str, Dict[str, Any]],
    sync_home: Path | None = None,
) -> int:
    """执行导出：将 delta.json + changed 文件打包为分片文本。

    返回分片数量。
    """
    main_dir = _get_main_dir(vault_root)
    sync_home = sync_home or vault_root
    out_dir = sync_home / config.SYNC_DIR / config.OUT_DIR

    # 1. 构建 zip 内存缓冲区
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 写入 delta.json
        zf.writestr(config.DELTA_FILE, json.dumps(delta, ensure_ascii=False, indent=2))

        # 写入 changed 文件
        for item in delta["changed"]:
            rel = item["path"]
            abs_path = main_dir / rel
            if abs_path.is_file():
                zf.write(abs_path, rel)
            else:
                log_warn(f"导出时文件已缺失：{rel}")

    zip_bytes = buf.getvalue()
    log_info(f"zip 大小：{len(zip_bytes)} bytes")

    # 2. base64 编码
    b64_str = base64.b64encode(zip_bytes).decode("ascii")

    # 3. 分片
    out_dir.mkdir(parents=True, exist_ok=True)
    # 清理旧分片
    for old in out_dir.glob(f"{config.PART_PREFIX}*{config.PART_SUFFIX}"):
        old.unlink()

    total = len(b64_str)
    part_count = 0
    offset = 0
    while offset < total:
        part_count += 1
        chunk = b64_str[offset : offset + config.CHUNK_SIZE]
        fname = f"{config.PART_PREFIX}{str(part_count).zfill(config.PART_NUM_WIDTH)}{config.PART_SUFFIX}"
        (out_dir / fname).write_text(chunk, encoding="utf-8")
        offset += config.CHUNK_SIZE

    log_info(f"导出完成：{part_count} 个分片，输出到 {out_dir}")
    return part_count
