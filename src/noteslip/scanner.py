"""扫描 main 目录，生成 manifest（文件哈希清单）"""

from pathlib import Path
from typing import Dict, Any

from . import config
from .utils import sha256_of_file, rel_posix, log_info, is_path_safe


def scan_main(vault_root: Path) -> Dict[str, Dict[str, Any]]:
    """扫描 vault_root/main/**/*.md，返回 manifest dict。

    返回格式：
        {
            "notes/test.md": {"sha256": "...", "size": 123, "mtime": "2026-04-18T12:00:00"},
            ...
        }
    路径均为相对 main 的 POSIX 路径。
    """
    main_dir = vault_root / config.MAIN_DIR
    if not main_dir.is_dir():
        log_info(f"main 目录不存在：{main_dir}")
        return {}

    manifest: Dict[str, Dict[str, Any]] = {}
    for fpath in sorted(main_dir.glob(config.GLOB_PATTERN)):
        # 跳过 .conflicts 目录下的文件
        rel = rel_posix(main_dir, fpath)
        if not is_path_safe(rel):
            continue
        # 排除 .conflicts 前缀
        first_part = rel.split("/")[0]
        if first_part in config.EXCLUDED_PREFIXES:
            continue

        stat = fpath.stat()
        manifest[rel] = {
            "sha256": sha256_of_file(fpath),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    log_info(f"扫描完成，共 {len(manifest)} 个 md 文件")
    return manifest
