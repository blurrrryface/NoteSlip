---
name: NoteSlip 双向增量同步工具
overview: 实现一个基于纯文本分片传输的双向增量 Markdown 笔记同步 CLI 工具，支持 Export（扫描增量→打包→分片）和 Import（合并分片→解包→应用变更→冲突处理），核心保证不丢数据、冲突落到 .conflicts 目录。
todos:
  - id: project-scaffold
    content: 创建包结构：src/noteslip/ 所有模块文件、config.py 常量、__init__.py 版本号，更新 pyproject.toml 入口点
    status: completed
  - id: scanner-and-utils
    content: 实现 utils.py（sha256分块计算、路径安全校验、日志）和 scanner.py（扫描 main 目录生成 manifest）
    status: completed
    dependencies:
      - project-scaffold
  - id: state-manager
    content: 实现 state.py：state.json 的加载/保存/更新，export_base 与 peer_tokens 管理
    status: completed
    dependencies:
      - scanner-and-utils
  - id: delta-and-export
    content: 实现 delta.py（差量计算）和 exporter.py（zip打包→base64→分片），以及 init 和 export 子命令
    status: completed
    dependencies:
      - state-manager
  - id: importer-and-cli
    content: 实现 importer.py（合片→解码→解包→校验→冲突检测→应用变更）和 import 子命令，完成 main.py CLI 入口
    status: completed
    dependencies:
      - delta-and-export
  - id: readme-docs
    content: 更新 README.md：安装方式、初始化、导出/导入操作流程、冲突解决指南
    status: completed
    dependencies:
      - importer-and-cli
---

## 产品概述

NoteSlip 是一个命令行工具，用于两台 Windows 电脑之间双向增量同步 Markdown 笔记库。通过"导出纯文本包 → 搬运 → 导入"的方式实现同步，不依赖云盘或实时连接。

## 核心功能

- **初始化 (init)**：指定库路径和端标识（home/work），创建 `.sync` 目录结构和 `state.json`
- **导出 (export)**：扫描 `main\**.md`，对比上次导出基线算出增量（新增/修改/删除），打成 zip → base64 → ~900KB 分片输出到 `.sync\out\`
- **导入 (import)**：从 `.sync\in\` 收集分片 → 合并解码解包 → 校验（防重复/顺序提示）→ 应用变更，冲突文件落入 `main\.conflicts\`
- **冲突策略**：修改冲突写对端版本到 `.conflicts`，删除冲突保留本地版本并写标记文件；冲突需手工合并后再导出同步
- **状态管理**：`state.json` 记录导出基线和已导入包 ID，`basePeerToken` 提供顺序提示防缺包

## 技术栈

- 语言：Python 3.12+
- CLI：argparse（标准库，零依赖）
- 核心依赖全部使用标准库：hashlib, zipfile, base64, json, pathlib, uuid, os, shutil, datetime
- 无第三方依赖

## 实现方案

### 整体策略

将同步拆为 init / export / import 三个子命令，以 `argparse` 组织 CLI。核心流程：扫描 → 差量计算 → 打包编码分片（导出端），合片解码解包 → 校验 → 冲突检测 → 应用（导入端）。

### 关键设计决策

1. **全部标准库**：hashlib(sha256) / zipfile / base64 / json / uuid 已满足所有需求，无需引入第三方包，降低部署门槛
2. **state.json 作为唯一真相源**：导出基线、对端 token、已导入记录集中管理，避免多文件不一致
3. **冲突检测基于 hash 对比**：导入时用当前文件 sha256 与 export_base 中的 hash 比较，不同则视为本地有并行修改
4. **basePeerToken 用导出时的 packageId**：简单可靠，导入时检查是否与本地记录的 last_imported_token 匹配即可提示缺包

### 性能考量

- 扫描时逐文件计算 sha256，对大文件使用分块读取（8KB 块）避免内存溢出
- zip 压缩对 md 文件效果好（通常 60-70% 压缩率），base64 膨胀约 33%，综合后分片数可控
- 导入时先校验 packageId 再解包，避免重复工作

### 目录结构

```
d:\NoteSlip\
├── main.py                          # [MODIFY] CLI 入口，argparse 定义子命令并分发
├── pyproject.toml                   # [MODIFY] 添加 scripts 入口点
├── README.md                        # [MODIFY] 补充使用文档
├── src/
│   └── noteslip/
│       ├── __init__.py              # [NEW] 包初始化，版本号
│       ├── config.py                # [NEW] 常量定义：目录名、分片大小、排除规则
│       ├── scanner.py               # [NEW] 扫描 main\**.md，计算 sha256，返回 manifest
│       ├── state.py                 # [NEW] state.json 读写、export_base 管理、peer token 管理
│       ├── delta.py                 # [NEW] 差量计算：对比当前 manifest 与 export_base，生成 delta.json
│       ├── exporter.py              # [NEW] 打包流程：delta+files→zip→base64→分片写入 .sync\out\
│       ├── importer.py              # [NEW] 导入流程：合片→解码→解包→校验→冲突检测→应用变更
│       └── utils.py                 # [NEW] 通用工具：sha256计算、路径安全校验、日志输出
```

### 关键数据结构

**state.json**

```
{
  "side": "home",
  "export_base": {
    "relative/path.md": { "sha256": "...", "size": 123, "mtime": "2026-04-18T12:00:00" }
  },
  "last_export_token": "pkg-uuid-001",
  "peer_tokens": { "work": "pkg-uuid-003" },
  "imported_ids": ["pkg-uuid-002"]
}
```

**delta.json**

```
{
  "packageId": "uuid4",
  "fromSide": "home",
  "createdAt": "2026-04-18T12:00:00",
  "basePeerToken": "pkg-uuid-003",
  "changed": [
    { "path": "notes/test.md", "sha256": "...", "size": 100, "mtime": "..." }
  ],
  "deleted": ["old/deleted.md"]
}
```

### 实现注意事项

- Windows 路径处理统一用 `pathlib.PurePosixPath` 存储相对路径（跨机器一致性），磁盘操作用 `pathlib.Path`
- 导入时路径安全校验：禁止 `..` 跳出 main 目录的路径注入
- 分片命名 `part001.txt`，编号固定3位，合并时按数字排序
- zip 内文件用相对路径存储，解包时校验目标路径在 main 目录内
- 冲突文件路径中 `/` 替换为 `__` 以避免深层嵌套问题，同时保留原始路径信息便于定位