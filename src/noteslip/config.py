"""全局常量与配置"""

from pathlib import Path

# ── 目录名 ──────────────────────────────────────────────
MAIN_DIR = ""  # 空字符串表示 vault 根目录即为笔记目录
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
# 默认同步的文件扩展名，可通过 NOTESLIP_EXTENSIONS 环境变量覆盖
# 环境变量格式：逗号分隔，如 ".md,.py,.txt"
DEFAULT_EXTENSIONS = (".md",)
GLOB_PATTERN = "**/*"  # 匹配所有文件，由扩展名过滤

# ── 冲突文件命名 ──────────────────────────────────────────
CONFLICT_SEP = "__"
CONFLICT_TAG = "CONFLICT"
DELETE_CONFLICT_TAG = "DELETE_CONFLICT"
CONFLICT_FROM_PREFIX = "from_"

# ── 排除目录（扫描时跳过，第一级目录名） ────────────────────
EXCLUDED_PREFIXES = (CONFLICTS_DIR, SYNC_DIR)

# ── 哈希 ────────────────────────────────────────────────
HASH_BUF_SIZE = 8192  # 8KB 分块读
