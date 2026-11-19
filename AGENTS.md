# AI Development Instructions

本仓库当前处于 AI 开发阶段 1：人审核工作，AI 执行开发，人完成最终验收。

开始任何工作前必须阅读：

1. [Vibe Coding 开发规范](./docs/development/vibe-coding.md)
2. [文档管理规范](./docs/development/documentation.md)
3. 当前 Issue 及其关联的产品、功能、架构和领域文档

硬性规则：

- Feature、Bug、Chore 或 Research 必须有对应 Issue。
- 只有人可以将 Issue 从 `Human Review` 移到 `Ready`。
- AI 只能实现 `Ready` Issue，一次只处理一个 Issue。
- 开工前确认目标、范围、验收标准、风险等级、依赖和 AI 能力对等要求。
- 事实可以通过代码和工具查证；缺失的业务决策必须交给人决定。
- 管理员拥有的每项业务能力必须提供对应的 AI 结构化接口。
- 不得绕过权限、审计、测试或迁移要求来加快交付。
- 获批任务所需的构建、CI 修复、既定环境部署、启动、运行验证和失败回退由 Codex 直接完成，遵循[常规工程交付](./docs/development/vibe-coding.md#86-常规工程交付)，不单独请求部署批准。
- 默认不安装浏览器或执行浏览器页面验收；工程检查和部署完成后交由用户验收页面与交互，停在 `In Review`。
- 改动保持聚焦，不处理当前 Issue 范围外的问题；额外问题创建或建议新 Issue。
- 完成后提供逐条验收证据、测试结果、文档影响和剩余风险。
- AI 将工作提交到 `In Review` 后停止；不得自行合并或标记 `Done`。
- 未经人批准的 `Loop Mandate`，不得自动领取下一项工作。

若本文件与完整规范不一致，以 [Vibe Coding 开发规范](./docs/development/vibe-coding.md) 为准，并报告差异。
