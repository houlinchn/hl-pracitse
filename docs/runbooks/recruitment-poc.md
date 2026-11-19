# 核心招聘 POC：运行与验收

本手册仅适用于 [Issue #2](https://github.com/houlinchn/hl-pracitse/issues/2) 的隔离演示。它不是生产部署或完整 Recruitment MVP。只使用演示数据；职位为示例，不代表真实招聘、福利、薪资或政策。

## 前置条件与隔离边界

- Docker + Compose v2 或更高、Git、Python 3（用于生成配置和健康检查）。完整容器运行不要求宿主机安装 Python 3.13 或 Node。
- 本地开发与测试另需 uv、Python 3.13（uv 可下载）、Node 24、pnpm 10.34.9。依赖由 `backend/uv.lock` 和 `frontend/pnpm-lock.yaml` 锁定。
- 必须在本仓库的独立 worktree / Issue 分支操作。先确认 `git branch --show-current`，不要修改原仓库 main 或用户工作区。
- Compose 项目固定为 `hl-pracitse-poc`，独立网络 `hl-pracitse-poc_default`、卷 `hl-pracitse-poc_poc-postgres`。不连接现有代理或业务网络。
- 端口固定绑定 **127.0.0.1**：13080 网页、13081 API、13082 PostgreSQL。先用 `ss -ltn` 确认空闲；占用时不要停止其他服务，先调整本 POC 配置及 `APP_ORIGIN`、测试地址。
- 不修改反代、DNS、防火墙、公网端口或 systemd。不运行全局 prune。

## 首次启动

从仓库根目录执行：

```bash
./scripts/poc.sh up
./scripts/poc.sh staff
./scripts/poc.sh status
```

`up` 顺序执行本地配置、锁定依赖镜像构建、专用 PostgreSQL 启动、显式 schema 初始化、前后端启动和 HTTP 健康检查。`staff` 是单独、显式的员工创建步骤，创建演示员工 `staff@example.com`，具有 `applications.read`、`applications.advance`、`audit.read`。重复创建会失败，不覆盖密码、不将已有申请人提权。以后启动只需 `up`。

配置生成器不会覆盖已有值：

| 本地文件 | 内容 | 保护 |
| --- | --- | --- |
| `.env` | 专用随机数据库密码、宿主开发连接地址、网页 Origin、Cookie 配置 | gitignored、600 |
| `.local/staff-password` | 本次本机生成的独立员工密码 | gitignored、600；目录 700 |

密码不在代码、日志或报告中显示。人工登录时从本机私密文件取得；不要粘贴到 Issue / PR。公开注册永远只创建申请人。需要其他员工时，可执行以下命令交互输入独立密码：

```bash
docker compose -p hl-pracitse-poc run --rm --no-deps api \
  uv run --frozen --no-dev python -m poc.cli create-staff \
  --email reviewer@example.com --permission applications.read --permission audit.read
```

也可用当前用户所有、600 权限的 `--password-file`；容器调用时需只读挂载该文件，并将一次性 CLI 容器的 UID/GID 设为文件所有者（`scripts/poc.sh staff` 已处理）。常驻 API 不挂载员工密码文件。可重复指定 `--application-id UUID` 收窄员工对象范围，未指定时可访问全部已提交申请。员工只读角色不会获得推进或审计权限。

访问：

- 网页：<http://127.0.0.1:13080>
- FastAPI 文档：<http://127.0.0.1:13081/docs>；OpenAPI：`/openapi.json`
- 健康检查：`curl --fail --max-time 5 http://127.0.0.1:13080/api/health`

远程服务器需要 SSH 转发；在自己的电脑执行（主机名和 SSH 端口按实际连接修改）：

```bash
ssh -L 13080:127.0.0.1:13080 -L 13081:127.0.0.1:13081 your-server
```

浏览器必须使用 `http://127.0.0.1:13080`，不要改成 `localhost`（Origin 严格匹配）。这不建立公网部署。

## 人工页面验收

1. 在首页选择“创建申请人账号”，使用 `alex-unique@example.com` 等演示邮箱和自选 12–128 字符密码。
2. 填写示例姓名、联系邮箱和申请说明；验证无效邮箱、空字段会阻止保存；保存草稿，再修改并保存。
3. 草稿只对本人可见。核对保存内容后“确认提交”；页面状态为“已提交”，资料不可继续编辑。刷新或退出再登录，应保持相同内容和状态。
4. 退出申请人账号，使用显式初始化的员工登录。按状态查看申请列表、打开详情；填写原因后“推进至初筛”。空白原因不可提交。
5. 查看状态记录和此申请的审计记录：包括执行主体、网页渠道、前后状态、原因和时间。初筛后的继续推进、回退、拒绝、录用和重新申请不在本 POC 内。
6. 在第二个演示申请上，通过“AI 委托”生成只限当前申请、所需权限的短期令牌，用下节结构化请求推进。回到申请管理刷新，应看到 AI 渠道、真实委托人和相同最新状态。
7. 撤销该委托后，再调用 AI 接口应为 401。不要保存令牌截图。以另一申请人登录不能读取前一个人的申请。
8. 在窄屏检查菜单、资料表单、列表、详情和错误提示。最终人工验收、合并、Done 均由人执行。

POC 每个申请人只支持一份申请；初筛不是录用。员工看不到未提交草稿。列表每页最多 50（API 可指定 1–100），按创建时间和 ID 排序；页面统计只计算当前页，审计展示最近 100 条。

## 权限、委托与结构化 AI 接口

| 员工业务能力 | 网页服务端入口 | AI 入口 | 权限 |
| --- | --- | --- | --- |
| 列表、状态筛选、分页 | `GET /api/staff/applications` | `GET /api/ai/applications` | `applications.read` |
| 详情与状态历史 | `GET /api/staff/applications/{id}` | `GET /api/ai/applications/{id}` | `applications.read` |
| 已提交 → 初筛 | `POST /api/staff/applications/{id}/advance` | `POST /api/ai/applications/{id}/advance` | `applications.advance` |
| 此申请的审计读取 | `GET /api/staff/applications/{id}/audit` | `GET /api/ai/applications/{id}/audit` | `audit.read` |

两组路由直接绑定 `backend/poc/applications.py` 的同一业务服务。所有对象访问取员工当前对象范围与委托对象范围的交集；当前权限与授权权限也取交集。权限收窄、账号停用、委托过期或撤销立即在后续认证请求中生效。

网页身份由随机不透明 Session Cookie 认证（HttpOnly、SameSite=Strict、8 小时有效）；可变更的网页请求必须提供严格匹配的 `Origin`。本机 HTTP 演示使用 `COOKIE_SECURE=false`，只绑定 loopback，不能直接用于公网。

AI 入口只接受 **Bearer 委托令牌**，拒绝网页会话令牌、Cookie 身份、无效 / 过期 / 撤销委托，不允许 AI 再委托。员工可从页面或本人 Session 创建 `POST /api/delegations`：

```json
{
  "permissions": ["applications.read", "applications.advance", "audit.read"],
  "application_ids": ["申请的 UUID"],
  "minutes": 15
}
```

`application_ids: null` 继承本人对象范围，`[]` 表示没有对象权限；有效期允许 1–60 分钟。`GET /api/delegations` 仅返回本人最近委托的元数据，不返回令牌；`DELETE /api/delegations/{id}` 仅能撤销本人的委托。委托管理是网页身份的安全控制面，不是可由 AI 再扩张的招聘业务能力。

在 API 文档 Authorize 中选择 `AIDelegation`，填入短期令牌。结构化推进的请求体示例：

```json
{
  "expected_version": 2,
  "reason": "演示：已核对样例资料，进入初筛"
}
```

`expected_version` 必须来自最新详情响应；并发或过期视图返回 409，刷新后重新核对。不接受客户端传入的 `actor_id`、`delegated_by` 或目标状态；身份取自后端凭据。执行主体记为 `ai:<委托ID>`，委托人为真实员工 ID，渠道为 `ai`。普通网页操作执行主体为已认证账号 ID，渠道为 `web`。

成功变更、状态事件、成功审计在同一 PostgreSQL 事务提交；状态变更使用 `SELECT … FOR UPDATE` 和版本核对。初次创建有 `null → draft` 事件。审计只记录动作、字段名、版本、筛选条件、结果及状态原因等必要信息，不保存密码、令牌或整份申请说明。查询也会审计；已认证失败请求在独立事务记录最小拒绝信息，不会写成功事件。数据库故障返回通用 503；数据库不可用时不能保证写入拒绝审计。审计与事件表有防 UPDATE / DELETE 的数据库触发器；DB 所有者仍有 DDL 权限，因此本演示不是不可篡改的生产审计存储。

状态码约定：401 身份无效，403 缺少动作权限或 Origin 不符，404 对象不存在 / 不可访问（避免泄露对象存在性），409 版本或状态冲突 / 重复申请，422 输入校验失败，503 数据库操作失败。校验错误只回显字段名，不回显原始输入。

## 本地开发与自动化复核

保留 Compose 的专用 `db`；若改用宿主开发进程，先停止本 POC 的 `api web`，避免端口冲突。

```bash
uv sync --project backend --python 3.13 --frozen
pnpm --dir frontend install --frozen-lockfile
uv run --directory backend --env-file ../.env python -m poc.cli init-db
# 两个独立终端；保持仅 loopback
uv run --directory backend --env-file ../.env uvicorn poc.main:app --host 127.0.0.1 --port 13081 --no-access-log
pnpm --dir frontend dev
```

完整验证在仓库根目录执行：

```bash
# 会创建 recruitment_poc_test；仅此测试库会在每例测试前 TRUNCATE
uv run --project backend --env-file .env python scripts/test_backend.py
uv run --project backend ruff check --config backend/pyproject.toml backend scripts
uv run --project backend ruff format --check --config backend/pyproject.toml backend scripts
pnpm --dir frontend typecheck
pnpm --dir frontend build
# 需要完整 POC 在线且已显式初始化 staff@example.com
uv run --project backend python scripts/smoke.py
# 可选：停止并重新启动仅本 POC 全栈，验证卷和会话持久化
uv run --project backend python scripts/smoke.py --restart
```

页面、视觉及交互由用户在部署后验收。默认 CI 不安装浏览器、不执行浏览器页面验收。仓库保留 Playwright 用例作为可选工具，仅在用户明确要求自动化浏览器测试时使用；下述浏览器说明不代表默认执行要求。

测试入口和 fixture 均校验固定的 loopback 13082、poc 账号与专用测试库名；不接受任意 DATABASE_URL 作为清库目标。测试包括正常、非法输入、权限与对象越权、身份伪造、委托权限收窄 / 过期 / 撤销、状态冲突、重复和四并发写入、人机混合并发、真实数据库故障回滚、历史防篡改与 CLI 创建员工。

Playwright 使用 Chromium 的桌面和 Pixel 7 视口执行完整链路（移动为仿真，不是物理设备）。需要浏览器运行库和中文字体；缺少时可在隔离 CI 环境运行 `playwright install --with-deps chromium`，或在本机用户目录解压所需库并设置 `LD_LIBRARY_PATH`。本机具体路径见机器记忆 / HANDOFF。无法启动浏览器必须如实记为未验证。测试产生的截图仅含演示资料，位于 gitignored `frontend/test-results/`；禁用 trace / video，不抓取令牌页面，测试产物使用 077 umask。全链路测试会在 POC 主演示库添加随机命名的样例账号和申请；不会清理其他数据。

## 初始化、数据恢复与清理

此 schema 是全新的隔离 POC，按既有架构约定暂缓 Alembic。`init-db` 幂等创建表和历史保护触发器，不自动改造已存在表结构。进入 MVP 前必须建立迁移与回退链；不能把 `create_all` 当作升级工具。需要重建本 POC 数据时，先停止服务、确认项目名与卷归属；以下操作不适用于任何已有业务库。

停止服务并保留所有演示数据：

```bash
./scripts/poc.sh stop
```

移除仅本 POC 的容器和默认网络，保留卷（下次 `up` 恢复）：

```bash
./scripts/poc.sh down
```

确认不再需要演示 / 测试数据后，可删除仅本 POC 的专用卷：

```bash
docker volume inspect hl-pracitse-poc_poc-postgres --format '{{json .Labels}}'
# 确认 com.docker.compose.project 为 hl-pracitse-poc 后，才执行：
docker compose -p hl-pracitse-poc down --volumes
```

删除卷会清空 POC 两个数据库，无法撤回；凭据文件仍留在本工作树，重新 `up` + `staff` 建立空环境。不要使用全局 prune。需要保留样例数据可在停机前用 `pg_dump` 保存到 gitignored、600 文件，但本 POC 未声明生产备份 / 恢复能力。

## 已知边界与人工重点

只支持三状态与最小资料，不含真实招聘政策、附件、邮件、后续面试 / 入职、财务、MFA、正式限流、密码重置、邮箱验证、生产迁移、备份、TLS 或高可用。不要使用真实个人信息或复用真实密码。运行镜像的基础 tag 不锁 digest；应用依赖已锁定。人应重点复核权限与委托边界、审计可读性、实际页面体验、隔离清理方法。CI 检查成为 main 必需检查的配置由仓库维护者复核；AI 不改变主分支保护或自行合并。
