"""全局常量与配置"""

from pathlib import Path

# ── 目录名 ──────────────────────────────────────────────
MAIN_DIR = "main"
SYNC_DIR = ".sync"
CONFLICTS_DIR = ".conflicts"
OUT_DIR = "out"
IN_DIR = "in"

# ── 文件名 ──────────────────────────────────────────────
STATE_FILE = "state.json"
IMPORTED_LOG = "imported.log"
DELTA_FILE = "delta.json"

# ── 分片 ────────────────────────────────────────────────
PART_PREFIX = "part"
PART_SUFFIX = ".txt"
PART_NUM_WIDTH = 3  # part001, part002 ...
CHUNK_SIZE = 900 * 1024  # 900 KB

# ── 扫描 ────────────────────────────────────────────────
GLOB_PATTERN = "**/*.md"

# ── 冲突文件命名 ──────────────────────────────────────────
CONFLICT_SEP = "__"
CONFLICT_TAG = "CONFLICT"
DELETE_CONFLICT_TAG = "DELETE_CONFLICT"
CONFLICT_FROM_PREFIX = "from_"

# ── 排除目录（相对 main 的路径片段） ────────────────────────
EXCLUDED_PREFIXES = (CONFLICTS_DIR,)

# ── 哈希 ────────────────────────────────────────────────
HASH_BUF_SIZE = 8192  # 8KB 分块读
