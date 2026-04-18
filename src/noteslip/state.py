"""同步状态管理：state.json 读写与更新"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from . import config
from .utils import log_info, log_warn


class SyncState:
    """封装 .sync/state.json 的读写操作。"""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self.sync_dir = vault_root / config.SYNC_DIR
        self.state_path = self.sync_dir / config.STATE_FILE
        self._data: Dict[str, Any] = {}

    # ── 加载 / 保存 ──────────────────────────────────────

    def load(self) -> "SyncState":
        if self.state_path.is_file():
            with open(self.state_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            raise FileNotFoundError(
                f"state.json 不存在，请先运行 noteslip init：{self.state_path}"
            )
        return self

    def save(self) -> None:
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── 属性访问 ──────────────────────────────────────────

    @property
    def side(self) -> str:
        return self._data.get("side", "")

    @property
    def export_base(self) -> Dict[str, Any]:
        return self._data.get("export_base", {})

    @export_base.setter
    def export_base(self, value: Dict[str, Any]) -> None:
        self._data["export_base"] = value

    @property
    def last_export_token(self) -> Optional[str]:
        return self._data.get("last_export_token")

    @last_export_token.setter
    def last_export_token(self, value: str) -> None:
        self._data["last_export_token"] = value

    @property
    def peer_tokens(self) -> Dict[str, str]:
        return self._data.get("peer_tokens", {})

    @property
    def imported_ids(self) -> list:
        return self._data.get("imported_ids", [])

    # ── 更新操作 ──────────────────────────────────────────

    def add_imported_id(self, package_id: str) -> None:
        ids = self._data.get("imported_ids", [])
        if package_id not in ids:
            ids.append(package_id)
        self._data["imported_ids"] = ids

    def update_peer_token(self, from_side: str, package_id: str) -> None:
        tokens = self._data.get("peer_tokens", {})
        tokens[from_side] = package_id
        self._data["peer_tokens"] = tokens

    def is_imported(self, package_id: str) -> bool:
        return package_id in self._data.get("imported_ids", [])

    def get_peer_token(self, side: str) -> Optional[str]:
        return self._data.get("peer_tokens", {}).get(side)

    # ── 初始化 ──────────────────────────────────────────

    @classmethod
    def init(cls, vault_root: Path, side: str) -> "SyncState":
        """创建新的 state.json。"""
        st = cls(vault_root)
        st._data = {
            "side": side,
            "export_base": {},
            "last_export_token": None,
            "peer_tokens": {},
            "imported_ids": [],
        }
        st.save()
        log_info(f"已初始化：side={side}, vault={vault_root}")
        return st
