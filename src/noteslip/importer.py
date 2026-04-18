"""导入流程：合片 → 解码 → 解包 → 校验 → 冲突检测 → 应用变更"""

import base64
import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

from . import config
from .scanner import _get_main_dir
from .state import SyncState
from .utils import sha256_of_file, log_info, log_warn, log_error, is_path_safe


def import_package(vault_root: Path, state: SyncState, sync_home: Path | None = None) -> None:
    """从 .sync/in/ 读取分片，执行完整导入流程。"""
    sync_home = sync_home or vault_root
    in_dir = sync_home / config.SYNC_DIR / config.IN_DIR
    main_dir = _get_main_dir(vault_root)
    conflicts_dir = vault_root / config.CONFLICTS_DIR

    # 1. 收集分片 → 合并
    parts = sorted(in_dir.glob(f"{config.PART_PREFIX}*{config.PART_SUFFIX}"))
    if not parts:
        log_error("未找到任何分片文件，请将 part*.txt 放入 .sync/in/ 目录")
        return

    b64_str = ""
    for p in parts:
        b64_str += p.read_text(encoding="utf-8")

    # 2. 解码 → 解包
    try:
        zip_bytes = base64.b64decode(b64_str)
    except Exception as e:
        log_error(f"base64 解码失败：{e}")
        return

    unpack_dir = sync_home / config.SYNC_DIR / "_unpack"
    if unpack_dir.exists():
        shutil.rmtree(unpack_dir)
    unpack_dir.mkdir(parents=True)

    try:
        with zipfile.ZipFile(io_from_bytes(zip_bytes), "r") as zf:
            zf.extractall(unpack_dir)
    except Exception as e:
        log_error(f"zip 解包失败：{e}")
        return

    # 3. 读取 delta.json
    delta_path = unpack_dir / config.DELTA_FILE
    if not delta_path.is_file():
        log_error("包中缺少 delta.json")
        return

    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    package_id = delta["packageId"]
    from_side = delta["fromSide"]
    base_peer_token = delta.get("basePeerToken")

    # 4. 包级校验
    if state.is_imported(package_id):
        log_warn(f"包 {package_id[:8]}... 已导入过，跳过")
        return

    if base_peer_token:
        expected = state.get_peer_token(from_side)
        if expected and expected != base_peer_token:
            log_warn(
                f"⚠️ basePeerToken 不匹配！对端基于 {base_peer_token[:8]}... 导出，"
                f"但本机记录的对端最新 token 是 {expected[:8]}...，"
                f"可能缺少中间包，建议先补齐。"
            )

    # 5. 加载当前 export_base 作为冲突判定基线
    export_base = state.export_base

    # 6. 应用 changed
    for item in delta.get("changed", []):
        rel = item["path"]
        if not is_path_safe(rel):
            log_warn(f"跳过不安全路径：{rel}")
            continue

        src = unpack_dir / rel
        dst = main_dir / rel

        if not src.is_file():
            log_warn(f"包中缺少文件：{rel}")
            continue

        # 冲突检测：本地文件存在且与 export_base 中的 hash 不同
        if dst.is_file():
            local_hash = sha256_of_file(dst)
            base_hash = export_base.get(rel, {}).get("sha256")
            if base_hash and local_hash != base_hash:
                # 冲突：将远程版本放到 .conflicts
                conflict_name = _conflict_filename(rel, from_side, package_id, config.CONFLICT_TAG)
                conflict_path = conflicts_dir / conflict_name
                conflict_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, conflict_path)
                log_warn(f"⚠️ 冲突：{rel} → 远程版本已保存到 {conflict_path}")
                continue

        # 无冲突 → 直接写入
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log_info(f"已更新：{rel}")

    # 7. 应用 deleted
    for rel in delta.get("deleted", []):
        if not is_path_safe(rel):
            log_warn(f"跳过不安全删除路径：{rel}")
            continue

        dst = main_dir / rel

        if not dst.exists():
            # 文件已不存在，无需操作
            continue

        # 删除冲突检测：本地文件与 export_base hash 不同
        if dst.is_file():
            local_hash = sha256_of_file(dst)
            base_hash = export_base.get(rel, {}).get("sha256")
            if base_hash and local_hash != base_hash:
                # 删除冲突：保留本地，写标记文件
                conflict_name = _conflict_filename(
                    rel, from_side, package_id, config.DELETE_CONFLICT_TAG, ext=".txt"
                )
                conflict_path = conflicts_dir / conflict_name
                conflict_path.parent.mkdir(parents=True, exist_ok=True)
                conflict_path.write_text(
                    f"远程删除了此文件，但本地有未同步修改。\n"
                    f"路径：{rel}\n"
                    f"来自：{from_side}\n"
                    f"包 ID：{package_id}\n",
                    encoding="utf-8",
                )
                log_warn(f"⚠️ 删除冲突：{rel} → 保留本地版本，标记文件已写入 {conflict_path}")
                continue

        # 无冲突 → 删除
        dst.unlink()
        log_info(f"已删除：{rel}")

    # 8. 更新状态
    state.add_imported_id(package_id)
    state.update_peer_token(from_side, package_id)
    # 合并对端 manifest 到 export_base
    _merge_export_base(state, delta)
    state.save()

    # 9. 清理
    shutil.rmtree(unpack_dir, ignore_errors=True)
    for p in in_dir.glob(f"{config.PART_PREFIX}*{config.PART_SUFFIX}"):
        p.unlink()

    log_info(f"导入完成：packageId={package_id[:8]}...")


def _conflict_filename(
    rel: str,
    from_side: str,
    package_id: str,
    tag: str,
    ext: str = ".md",
) -> str:
    """生成冲突文件名，将路径中的 / 替换为 __ 以避免深层嵌套。"""
    flat = rel.replace("/", config.CONFLICT_SEP).replace("\\", config.CONFLICT_SEP)
    # 如果原始扩展名不是 .md/.txt，使用传入的 ext
    stem = Path(flat).stem if flat.endswith(ext) else flat
    return (
        f"{stem}"
        f"{config.CONFLICT_SEP}{tag}"
        f"{config.CONFLICT_SEP}{config.CONFLICT_FROM_PREFIX}{from_side}"
        f"{config.CONFLICT_SEP}{package_id[:8]}"
        f"{ext}"
    )


def _merge_export_base(state: SyncState, delta: Dict[str, Any]) -> None:
    """将导入的变更合并到 export_base，使下次导出基线同步更新。"""
    base = dict(state.export_base)

    # 应用 changed
    for item in delta.get("changed", []):
        base[item["path"]] = {
            "sha256": item["sha256"],
            "size": item["size"],
            "mtime": item.get("mtime", ""),
        }

    # 应用 deleted
    for rel in delta.get("deleted", []):
        base.pop(rel, None)

    state.export_base = base


def io_from_bytes(data: bytes):
    """将 bytes 包装为 file-like 对象供 ZipFile 使用。"""
    return io.BytesIO(data)
