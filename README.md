# Architecture Consistency Guardian 架构一致性守卫

你的 AI 编程助手是不是也这样——修了一个 bug，却在三个文件里留下了旧变量名？改了状态机，但 fallback 还在偷偷把流量导回旧逻辑？

这个 [OpenClaw](https://github.com/openclaw/openclaw) Skill 专治这个病。它把 AI Agent 的默认姿势从「哪里报错补哪里」，强制切换为 **全局扫描 → 唯一真源 → 成组修改 → 残留审计 → 回归验证** 的完整工作流。不是教模型写更好的代码，而是不让它偷懒只改半截。

## 解决什么问题

AI Agent(或人类)修代码时,常见的坏习惯:
- 只改当前文件,不管调用方、配置层、文档和测试
- 在一个地方改了变量名,其他 10 个地方还是旧名字
- 修了一个状态机分支,没检查其他模块是否还在用旧状态值
- 更新了配置路径,但硬编码的副本散落各处
- 删了旧模块,但 fallback 分支还在静默地把流量导回去
- 报告"已修复",却没检查旧逻辑是否还活着

这个 Skill 强制要求:**改代码前先看全局**。

## 适用场景

- 跨文件统一变量/字段/参数命名
- 状态机收口(统一状态值、迁移规则、写回入口)
- 清理 legacy 路径、fallback、已退役模块
- 统一配置来源(数据库路径、环境变量、运行时配置)
- 重构后同步文档与代码
- 修 bug 时发现根因可能是架构契约漂移

## 强制 8 阶段工作流

1. **归类** - 判断一致性问题类别(命名、状态机、配置路径等)
2. **识别唯一真源** - 找到权威文件,标记竞争真源
3. **全局扫描** - 搜索所有引用,不只看当前文件
4. **修改计划** - 列出受影响文件和具体改动,再动手
5. **成组执行** - 按顺序:真源 → 调用方 → 配置层 → 兼容层 → 测试 → 文档
6. **残留审计** - 搜索旧名称、旧状态、旧路径、旧 fallback 是否仍存在
7. **回归验证** - 跑测试、grep 旧名称零命中、验证配置解析
8. **结构化报告** - 输出:唯一真源、影响范围、已改内容、残留兼容层、验证结果

## 内置脚本

| 脚本 | 用途 |
|------|------|
| `scripts/grep_legacy.py` | 扫描旧名称/旧路径/旧状态残留 |
| `scripts/scan_contract_drift.py` | 检测多个竞争真源 |
| `scripts/summarize_impacts.py` | 聚合扫描结果生成影响面摘要 |

### 使用示例

```bash
# 扫描 legacy 残留
python3 scripts/grep_legacy.py /path/to/project old_status_field legacy_module_name

# 检测契约漂移(多处定义同一个东西)
python3 scripts/scan_contract_drift.py /path/to/project

# 管道:grep 结果 → 影响面摘要
python3 scripts/grep_legacy.py /path/to/project old_name --json | \
  python3 scripts/summarize_impacts.py --source-of-truth config.py
```

## 目录结构

```
architecture-consistency-guardian/
├── SKILL.md                    # 核心工作流与硬规则
├── references/
│   ├── workflow.md             # 详细工作流与决策分支
│   ├── output_template.md      # 结构化报告模板
│   ├── risk_patterns.md        # 8 种常见一致性风险模式
│   └── contract_template.md    # 架构契约文档模板
├── templates/
│   ├── consistency_report_template.md
│   └── architecture_contract_template.md
└── scripts/
    ├── grep_legacy.py
    ├── scan_contract_drift.py
    └── summarize_impacts.py
```

## 安装

### ClawHub（推荐）

```bash
clawhub install architecture-consistency-guardian
```

### skills.sh

```bash
npx skills add upsightx/architecture-consistency-guardian
```

### 手动安装

```bash
cp -r architecture-consistency-guardian ~/.openclaw/skills/
```

## License

MIT
