# 架构与技术选型

## 架构方向

第一阶段使用模块化单体，不拆分微服务。

```text
Nuxt 管理后台/教师门户 ─┐
                         ├─→ FastAPI 业务模块 → PostgreSQL
AI 工具                 ─┘                 └→ 文件存储
```

后端按业务能力组织，而不是按控制器、模型等技术类型组织。计划模块为：

```text
accounts          账号、认证和权限
recruitment       职位和招聘渠道
applications      教师申请和状态流转
interviews        Demo、面试和评价
documents         简历、证书和视频
compliance        身份与背景调查
teachers          在职教师档案和状态
onboarding        入职过程和事件
availability      每周可授课时间
payroll           工资周期和工资项目
rewards           奖励记录
notifications     邮件和站内通知
staff_portal      内部工作台和统计查询
ai_tools          AI 工具适配和委托信息
audit             操作审计
```

业务模块提供统一的查询和命令。HTTP 路由、管理员界面和 AI 工具只是调用这些能力的入口，不重复实现业务规则。

## POC 技术选型

为了尽快验证核心流程，POC 使用最小技术集合：

| 领域 | 技术 | 决定 |
| --- | --- | --- |
| 前端 | Nuxt 3、Vue 3、TypeScript | 同时支持官网 SEO、教师门户和后台 |
| 后端 | Python 3.13、FastAPI | 提供统一业务接口 |
| 数据校验 | Pydantic 2 | 保留；同时定义 HTTP 和 AI 工具输入输出 |
| 数据库 | PostgreSQL | 从 POC 开始使用，避免后续从 SQLite 迁移 |
| ORM | SQLAlchemy 2 | 使用 |
| 数据迁移 | Alembic | 一次性 POC 可暂缓；进入 MVP 时加入 |
| Python 依赖 | uv | 使用 `.venv`、`pyproject.toml` 和 `uv.lock` |
| 前端依赖 | pnpm | 使用 |
| 文件存储 | 本地目录 | POC 使用；MVP 再切换 Cloudflare R2 |
| 部署 | Docker Compose、Caddy | 需要部署共享环境时加入 |
| AI 接口 | OpenAPI 描述的结构化接口 | POC 先验证能力对等；需要接入 AI 客户端时增加 MCP 适配 |

POC 明确不引入：

- Redis
- Celery
- 微服务
- Kubernetes
- 独立搜索引擎
- 复杂事件总线

POC 中低风险通知可以使用 FastAPI `BackgroundTasks`。它不能保证进程重启后继续执行，因此不得用于工资确认、数据删除等关键任务。

## MVP 技术边界

进入 MVP 时必须补充：

- Alembic 数据库迁移
- Cloudflare R2 私有文件存储和临时签名链接
- 正式的角色权限和对象访问校验
- 管理员 MFA
- 登录与接口限流
- 数据库备份与恢复验证
- 文件类型、大小和病毒检查
- 完整审计和隐私数据删除流程

Redis 和 Celery 仍然不是 MVP 的默认依赖。只有出现以下明确需求时再引入：

- 任务必须可靠重试或在进程重启后继续
- 邮件、视频或文件扫描任务量影响接口响应
- 需要分布式锁或跨实例共享的高频缓存
- 需要大量定时任务及集中任务状态管理

## 核心招聘 POC 当前实现

- `frontend/`：Nuxt 3 + Vue 3 + TypeScript，同一个站点提供演示职位、申请人门户和员工工作台；Nitro 仅代理固定的 FastAPI upstream，不持有或伪造业务身份。
- `backend/poc/accounts.py`：scrypt 密码摘要、不透明会话和短期委托、当前权限与对象范围的交集。公开注册只创建申请人；员工通过 `poc.cli create-staff` 显式初始化。
- `backend/poc/applications.py`：申请查询、草稿编辑和三状态流转的唯一业务实现；网页与 AI HTTP 适配器共用服务、输入输出、权限和事务。
- `backend/poc/db.py`：SQLAlchemy 2 模型与请求事务；PostgreSQL 行锁 + 版本核对保证并发更新一致。业务变更、状态事件、成功审计原子提交；事件与审计分表并设 UPDATE / DELETE 保护触发器。
- AI 业务能力由 OpenAPI 描述的 `/api/ai` 提供，认证为后端签发、受限、可过期、可撤销的委托 Bearer；不会使用客户端 actor 字段。委托管理属于网页安全控制面，AI 不可再委托。
- 只实现草稿 → 已提交 → 初筛，草稿仅本人可见，每个申请人仅支持一份演示申请。未引入后续招聘和运营模块、文件存储或第三方集成。
- `compose.yaml`：独立 `hl-pracitse-poc` 项目、专用 PostgreSQL 卷与默认网络，三个服务只绑定 loopback。没有加入 Caddy 或现有反代。schema 显式初始化，暂缓 Alembic；只适用于新的隔离 POC，不能自动升级既有表结构。
- `backend/tests/` 使用真正 PostgreSQL 的独立测试库；`frontend/tests/` 用桌面 / 移动视口验证真实页面与 AI HTTP；`scripts/smoke.py` 验证完整容器网络链路。

当前接口、权限矩阵、操作边界与可执行复核步骤以 [POC runbook](../runbooks/recruitment-poc.md) 为运行入口。产品目标、领域术语、ADR 和开发治理未改变。
