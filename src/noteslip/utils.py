"""通用工具函数"""

import hashlib
import sys
from pathlib import Path

from . import config


def sha256_of_file(path: Path) -> str:
    """分块计算文件的 sha256，避免大文件内存溢出。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(config.HASH_BUF_SIZE)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def is_path_safe(rel_path: str) -> bool:
    """校验相对路径是否安全（不跳出笔记主目录）。

    禁止包含 '..' 段、绝对路径、空路径。
    """
    if not rel_path:
        return False
    if rel_path.startswith("/") or rel_path.startswith("\\"):
        return False
    parts = Path(rel_path).parts
    return ".." not in parts


def rel_posix(base: Path, full: Path) -> str:
    """计算 full 相对于 base 的 POSIX 路径字符串。"""
    return full.relative_to(base).as_posix()


def log_info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stdout)


def log_warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
