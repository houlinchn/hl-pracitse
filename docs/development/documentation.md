# 文档管理规范

## 目标

仓库文档保存项目的长期有效知识，使人和 AI 在新会话中都能恢复正确上下文。GitHub Issues 保存动态工作状态，Git 和 Pull Requests 保存实现与审查历史。

## 唯一事实来源

| 信息 | 权威位置 | 不应存放在 |
| --- | --- | --- |
| 产品目标、用户和原则 | `docs/product/vision.md` | Issue checklist |
| 阶段目标和顺序 | `docs/product/roadmap.md` | 重复的任务清单 |
| 领域术语 | `CONTEXT.md` | 各模块自行定义的词汇表 |
| 跨 Issue 的稳定功能规则 | `docs/features/` | 单个 PR 描述 |
| 当前架构和模块职责 | `docs/architecture/` | Issue 评论 |
| 难以逆转的架构决定 | `docs/adr/` | 普通开发笔记 |
| 开发管理流程 | `docs/development/` | 多份 AI 提示词 |
| 部署、备份和恢复步骤 | `docs/runbooks/` | 聊天记录 |
| 动态需求和工作状态 | GitHub Issues / Projects | Roadmap 复制列表 |
| 实现和审查历史 | Git commits / Pull Requests | 长期设计文档 |

同一信息只允许有一个权威位置，其他位置使用链接引用，不复制正文。

## 目录结构

```text
README.md                         文档总入口
CONTEXT.md                        统一领域术语

docs/
├── product/
│   ├── vision.md                 产品目标、用户和第一原则
│   └── roadmap.md                阶段目标与 Milestone
├── features/
│   └── <feature-name>.md         跨多个 Issue 的稳定功能规则
├── architecture/
│   └── overview.md               系统结构和模块职责
├── adr/
│   └── NNNN-<decision>.md        难以逆转的架构决策
├── development/
│   ├── vibe-coding.md            AI 协作和开发管理规范
│   └── documentation.md          本文档
└── runbooks/
    └── <operation>.md             部署、备份、恢复等操作手册
```

目录和文件按需创建，不创建空占位文档。

## 文档类型规则

### Feature 文档

仅当一个功能横跨多个 Issue，并且存在需要长期维护的业务规则时创建。单个 Issue 能完整表达的需求不创建 Feature 文档。

Feature 文档描述当前有效行为，不保存任务进度。进度由关联 Issue 管理。

### ADR

只有同时满足以下条件才创建：

1. 决定难以逆转。
2. 不记录原因会让后续维护者困惑。
3. 存在真实取舍并已选择其中一种方案。

### Runbook

Runbook 必须是可按顺序执行并能验证结果的操作说明。涉及生产变更时必须包含前置条件、验证和恢复方法。

## 更新规则

每个 Issue 完成前必须执行文档影响检查：

1. 是否改变产品范围或业务规则？
2. 是否新增或修改领域术语？
3. 是否改变架构、模块职责或技术边界？
4. 是否产生难以逆转的决定？
5. 是否改变部署、备份或恢复操作？
6. 是否改变开发管理流程？

有影响时在同一 PR 更新对应权威文档；无影响时在 PR 中明确写 `Documentation impact: none`。

## 写作规则

- 文档从 `README.md` 或上级索引可导航，禁止孤立文档。
- 使用项目在 `CONTEXT.md` 中确定的术语。
- 写当前事实和明确约束，不写未经确认的猜测。
- 动态状态、讨论过程和临时笔记留在 Issue 或 PR。
- 删除已失效内容；需要历史时依赖 Git，不在正文保留新旧两套规则。
- 文件名使用稳定、可搜索的小写英文和连字符。
- 链接使用仓库相对路径，并在移动文件后检查链接。
