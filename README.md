# Teacher Operations Platform

面向在线英语教师招聘和在职运营的一体化平台，供申请教师、内部员工和经授权的 AI 使用。

## 运行核心招聘 POC

本地演示已实现申请人注册登录、草稿编辑和提交、员工初筛、结构化 AI 对等接口、权限和审计。仅使用演示资料，流程止于初筛，不具备完整 MVP 或生产发布条件。

```bash
./scripts/poc.sh up
./scripts/poc.sh staff  # 首次显式创建随机密码员工；重复执行不会覆盖账号
```

网页：`http://127.0.0.1:13080`；API 文档：`http://127.0.0.1:13081/docs`。密码仅保存在 gitignored、600 权限的 `.local/staff-password`，不提供通用默认密码。

详见 [POC 运行、AI 接口与验收手册](./docs/runbooks/recruitment-poc.md)，含工具要求、远程访问、权限矩阵、测试、启动恢复和独立环境清理。停止仅本 POC：`./scripts/poc.sh stop`（保留数据）。

## 文档

- [领域语言](./CONTEXT.md)
- [产品愿景与范围](./docs/product/vision.md)
- [POC 路线图](./docs/product/roadmap.md)
- [架构与技术选型](./docs/architecture/overview.md)
- [Vibe Coding 开发规范](./docs/development/vibe-coding.md)
- [文档管理规范](./docs/development/documentation.md)
- [架构决策](./docs/adr/)
