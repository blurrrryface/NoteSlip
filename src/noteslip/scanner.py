"""扫描笔记目录，生成 manifest（文件哈希清单）"""

import os
from pathlib import Path
from typing import Dict, Any, Sequence

from . import config
from .utils import sha256_of_file, rel_posix, log_info, is_path_safe


def _get_main_dir(vault_root: Path) -> Path:
    """获取笔记主目录。MAIN_DIR 为空时返回 vault 根目录。"""
    if config.MAIN_DIR:
        return vault_root / config.MAIN_DIR
    return vault_root


def _get_extensions() -> Sequence[str]:
    """获取同步文件扩展名列表，优先从环境变量读取。"""
    env_ext = os.environ.get("NOTESLIP_EXTENSIONS", "").strip()
    if env_ext:
        return [e.strip() if e.strip().startswith(".") else f".{e.strip()}" for e in env_ext.split(",") if e.strip()]
    return config.DEFAULT_EXTENSIONS


def scan_main(vault_root: Path) -> Dict[str, Dict[str, Any]]:
    """扫描 vault 笔记目录，返回 manifest dict。

    根据配置的扩展名列表（默认 .md，可通过 NOTESLIP_EXTENSIONS 环境变量扩展）
    扫描匹配的文件。

    返回格式：
        {
            "notes/test.md": {"sha256": "...", "size": 123, "mtime": "2026-04-18T12:00:00"},
            ...
        }
    路径均为相对笔记主目录的 POSIX 路径。
    """
    main_dir = _get_main_dir(vault_root)
    if not main_dir.is_dir():
        log_info(f"笔记目录不存在：{main_dir}")
        return {}

    extensions = _get_extensions()
    manifest: Dict[str, Dict[str, Any]] = {}
    for fpath in sorted(main_dir.glob(config.GLOB_PATTERN)):
        if not fpath.is_file():
            continue
        # 按扩展名过滤
        if fpath.suffix.lower() not in extensions:
            continue
        # 跳过排除目录下的文件
        rel = rel_posix(main_dir, fpath)
        if not is_path_safe(rel):
            continue
        first_part = rel.split("/")[0]
        if first_part in config.EXCLUDED_PREFIXES:
            continue

        stat = fpath.stat()
        manifest[rel] = {
            "sha256": sha256_of_file(fpath),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    ext_str = ",".join(extensions)
    log_info(f"扫描完成，共 {len(manifest)} 个文件（扩展名：{ext_str}）")
    return manifest
