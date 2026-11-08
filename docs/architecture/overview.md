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
