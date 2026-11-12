# Voxnova

Voxnova 面向在线英语教师招聘和在职运营，服务申请人、内部员工和经授权的 AI。对外官网提供品牌、教师岗位、申请流程和常见问题入口。

## 运行与验收

产品已进入 Voxnova 招聘官网建设阶段。当前技术基础已实现申请人注册登录、草稿编辑与提交、员工初筛、结构化 AI 对等接口、权限和审计。品牌阶段变化不代表已补齐完整 MVP 的技术保障。

首页及现有申请人流程可通过「中文 / English」切换语言并记住选择；内部员工登录后使用中文。语言只影响界面，不翻译申请资料或改变业务数据。既定网站为 <https://careers.voxnova.cc/>，部署后提供精确版本和 HTTP 健康证据，由 owner 验收页面、窄屏布局及操作。

首页工程验证使用[专属隔离环境](./docs/runbooks/voxnova-home-validation.md)，与现有运行服务分开；默认不安装或运行浏览器验收。以下原 POC 入口仅供新的隔离演示使用，不应用于已有业务服务：

```bash
./scripts/poc.sh up
./scripts/poc.sh staff  # 首次显式创建随机密码员工；重复执行不会覆盖账号
```

网页：`http://127.0.0.1:13080`；API 文档：`http://127.0.0.1:13081/docs`。密码仅保存在 gitignored、600 权限的 `.local/staff-password`，不提供通用默认密码。

详见 [POC 运行、AI 接口与验收手册](./docs/runbooks/recruitment-poc.md)，含工具要求、远程访问、权限矩阵、测试、启动恢复和独立环境清理。停止仅本 POC：`./scripts/poc.sh stop`（保留数据）。

## 文档

- [领域语言](./CONTEXT.md)
- [产品愿景与范围](./docs/product/vision.md)
- [产品路线图](./docs/product/roadmap.md)
- [架构与技术选型](./docs/architecture/overview.md)
- [Vibe Coding 开发规范](./docs/development/vibe-coding.md)
- [文档管理规范](./docs/development/documentation.md)
- [架构决策](./docs/adr/)
- [GitHub Issue 开发监听器](./docs/runbooks/github-issue-agent.md)
