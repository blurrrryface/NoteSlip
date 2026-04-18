# NoteSlip

双向增量 Markdown 笔记同步工具——通过"导出纯文本包 → 搬运 → 导入"在两台电脑间同步笔记，不依赖云盘或实时连接。

## 特性

- **双向增量**：两边都能改，只传差异
- **纯文本传输**：变更打包为 base64 分片文本，可通过聊天、邮件、U盘搬运
- **冲突安全**：同一文件双方都改了不会丢数据，冲突版本存到 `.conflicts` 目录
- **零依赖**：纯 Python 标准库实现

## 安装

```bash
cd NoteSlip
pip install -e .
```

安装后即可使用 `noteslip` 命令。

## 环境变量配置

编辑项目根目录的 `.env` 文件，填入你的配置：

```ini
NOTESLIP_VAULT=D:\AgentSpace
NOTESLIP_SIDE=home
NOTESLIP_SYNC_HOME=D:\NoteSlip
NOTESLIP_PARTS_DIR=
```

| 环境变量 | 作用 | 示例值 |
|---|---|---|
| `NOTESLIP_VAULT` | 笔记目录 | `D:\AgentSpace` |
| `NOTESLIP_SIDE` | 本机标识（home 或 work） | `home` |
| `NOTESLIP_SYNC_HOME` | `.sync` 所在目录（默认与 vault 相同） | `D:\NoteSlip` |
| `NOTESLIP_PARTS_DIR` | 导入时的分片目录 | `D:\Downloads\parts` |

程序启动时会自动加载 `.env`，无需手动 source。项目提供了 `.env.example` 模板，复制后修改即可：

```bash
cp .env.example .env
```

## 使用方法

### 1. 初始化

在两台电脑上分别执行：

```bash
# 公司电脑
noteslip init work

# 家里电脑
noteslip init home
```

初始化后目录结构：

**默认（.sync 与笔记同目录）：**

```
D:\AgentSpace\           # vault（笔记目录）
├── note1.md             # 直接放在根目录的笔记
├── notes\
│   └── test.md          # 子目录中的笔记
├── .conflicts\          # 冲突文件（不同步）
└── .sync\               # 同步元数据
    ├── state.json
    ├── out\
    └── in\
```

**分离模式（.sync 在独立目录，通过 `--sync-home` 或 `NOTESLIP_SYNC_HOME` 指定）：**

```
D:\AgentSpace\           # vault（笔记目录）
├── note1.md
├── notes\
│   └── test.md
└── .conflicts\          # 冲突文件

D:\NoteSlip\             # sync_home（.sync 所在目录）
└── .sync\
    ├── state.json
    ├── out\
    └── in\
```

### 2. 导出

在改动端执行：

```bash
noteslip export
```

导出的分片文件在 `.sync\out\part001.txt`、`part002.txt`... 中。

### 3. 搬运分片

将 `.sync\out\` 中的所有 `part*.txt` 文件复制到另一台电脑。

### 4. 导入

在另一台电脑执行：

```bash
# 方式一：先把分片放入 .sync\in\ 再执行
noteslip import

# 方式二：设置了 NOTESLIP_PARTS_DIR 环境变量，自动从该目录读取
noteslip import
```

### 5. 处理冲突

导入后如果出现冲突：

1. 查看 `.conflicts\` 目录，找到冲突文件
2. 对比本地版本和远程版本（`.conflicts\<path>__CONFLICT__...`）
3. 手工合并为最终版本，保存到原路径
4. 删除 `.conflicts` 中对应的文件
5. 再次导出，将合并结果同步回对方

## 日常流程

```
公司改笔记 → noteslip export → 拷走 part*.txt
    ↓
家里 noteslip import → 没冲突则完成 / 有冲突则合并后再 export
    ↓
带回公司 noteslip import → 两边一致 ✓
```

反向同理（家里改 → 导出 → 公司导入）。

## 目录说明

| 目录/文件 | 说明 | 是否同步 |
|---|---|---|
| `**.md` | 笔记文件 | ✅ 同步范围 |
| `.conflicts\` | 冲突文件 | ❌ 不同步 |
| `.sync\state.json` | 同步状态基线 | ❌ 不同步 |
| `.sync\out\` | 导出分片 | ❌ 不同步 |
| `.sync\in\` | 导入分片 | ❌ 不同步 |

## 冲突策略

- **修改冲突**：双方都改了同一文件 → 远程版本存入 `.conflicts`，本地版本不动
- **删除冲突**：远程删了但本地又改了 → 保留本地版本，在 `.conflicts` 写标记文件
- **绝不丢数据**：冲突不会自动覆盖，需要人工裁决

## 命令参考

```
noteslip init <home|work>                 # 初始化
noteslip init home --sync-home D:\NoteSlip  # 初始化（.sync 分离模式）
noteslip export                           # 导出增量包
noteslip import                           # 导入增量包
```

通用参数：
- `--vault`：笔记目录（默认当前目录，可通过 `NOTESLIP_VAULT` 预设）
- `--sync-home`：`.sync` 所在目录（默认与 vault 相同，可通过 `NOTESLIP_SYNC_HOME` 预设）

## 注意事项

- 同步范围仅限 `**.md`，其他文件不会被同步
- 导入分片时确保按顺序放入 `.sync\in\`，文件名保持 `part001.txt` 格式
- 分片大小约 900KB，单条文本可安全粘贴到大部分聊天工具
