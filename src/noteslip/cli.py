"""NoteSlip CLI 入口"""

import argparse
import os
import sys
from pathlib import Path

from . import config
from .scanner import scan_main
from .state import SyncState
from .delta import compute_delta
from .exporter import export_package
from .importer import import_package
from .utils import log_info, log_error

# ── 环境变量 ──────────────────────────────────────────────
ENV_VAULT = "NOTESLIP_VAULT"
ENV_SIDE = "NOTESLIP_SIDE"
ENV_PARTS_DIR = "NOTESLIP_PARTS_DIR"
ENV_FILE = ".env"


def load_dotenv() -> None:
    """从当前目录或项目根目录加载 .env 文件到 os.environ。

    仅设置尚未存在的变量，不覆盖已有环境变量。
    .env 格式：KEY=VALUE，# 开头为注释，忽略空行。
    """
    search_paths = [Path.cwd()]
    # 也尝试从脚本所在目录往上找
    try:
        search_paths.append(Path(__file__).resolve().parent.parent.parent)
    except NameError:
        pass

    env_path = None
    for p in search_paths:
        candidate = p / ENV_FILE
        if candidate.is_file():
            env_path = candidate
            break

    if env_path is None:
        return

    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 去掉引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            # 只设置尚未存在的变量
            if key and key not in os.environ:
                os.environ[key] = value


def cmd_init(args) -> None:
    vault = Path(args.vault).resolve()
    side = args.side or os.environ.get(ENV_SIDE)

    if side is None:
        log_error(f"必须指定 side：命令行参数或设置 {ENV_SIDE} 环境变量（home/work）")
        sys.exit(1)

    if side not in ("home", "work"):
        log_error(f"side 必须是 home 或 work，当前：{side}")
        sys.exit(1)

    # 创建目录结构
    main_dir = vault / config.MAIN_DIR
    conflicts_dir = main_dir / config.CONFLICTS_DIR
    sync_dir = vault / config.SYNC_DIR
    out_dir = sync_dir / config.OUT_DIR
    in_dir = sync_dir / config.IN_DIR

    for d in (main_dir, conflicts_dir, sync_dir, out_dir, in_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 初始化 state
    state_path = sync_dir / config.STATE_FILE
    if state_path.exists():
        log_info(f"state.json 已存在，将重新初始化：{state_path}")

    SyncState.init(vault, side)
    log_info(f"初始化完成！vault={vault}, side={side}")


def cmd_export(args) -> None:
    vault = Path(args.vault).resolve()
    state = SyncState(vault).load()

    # 扫描当前 main
    current = scan_main(vault)

    # 计算差量
    # basePeerToken：取对端（非己方）的最新 token
    base_peer_token = None
    for side_name, token in state.peer_tokens.items():
        if side_name != state.side:
            base_peer_token = token
            break

    delta = compute_delta(current, state.export_base, state.side, base_peer_token)

    if not delta["changed"] and not delta["deleted"]:
        log_info("没有任何变更，无需导出")
        return

    # 打包导出
    part_count = export_package(vault, delta, current)

    # 更新状态
    state.export_base = current
    state.last_export_token = delta["packageId"]
    state.save()

    log_info(f"导出成功：{part_count} 个分片，packageId={delta['packageId'][:8]}...")


def cmd_import(args) -> None:
    vault = Path(args.vault).resolve()
    state = SyncState(vault).load()

    in_dir = vault / config.SYNC_DIR / config.IN_DIR

    # 如果提供了分片目录参数，复制文件到 .sync/in/
    if args.parts_dir:
        import shutil as shutil_mod

        parts_src = Path(args.parts_dir).resolve()
        if not parts_src.is_dir():
            log_error(f"分片目录不存在：{parts_src}")
            sys.exit(1)
        in_dir.mkdir(parents=True, exist_ok=True)
        # 清理旧分片
        for old in in_dir.glob(f"{config.PART_PREFIX}*{config.PART_SUFFIX}"):
            old.unlink()
        for f in sorted(parts_src.glob(f"{config.PART_PREFIX}*{config.PART_SUFFIX}")):
            shutil_mod.copy2(f, in_dir / f.name)

    import_package(vault, state)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="noteslip",
        description="NoteSlip - 双向增量 Markdown 笔记同步工具",
    )
    parser.add_argument(
        "--vault",
        default=os.environ.get(ENV_VAULT, "."),
        help=f"库根目录路径（默认当前目录，可通过 {ENV_VAULT} 环境变量预设）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── init ──────────────────────────────────────────
    p_init = sub.add_parser("init", help="初始化库")
    p_init.add_argument(
        "side",
        nargs="?",
        default=None,
        choices=["home", "work"],
        help=f"本机标识（可通过 {ENV_SIDE} 环境变量预设）",
    )

    # ── export ────────────────────────────────────────
    sub.add_parser("export", help="导出增量包")

    # ── import ────────────────────────────────────────
    p_import = sub.add_parser("import", help="导入增量包")
    p_import.add_argument(
        "--parts-dir",
        default=os.environ.get(ENV_PARTS_DIR),
        help=f"分片文件所在目录（可通过 {ENV_PARTS_DIR} 环境变量预设）",
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)


if __name__ == "__main__":
    main()
