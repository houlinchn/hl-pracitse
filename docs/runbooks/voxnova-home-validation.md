# Voxnova 首页：隔离工程验证与既定服务部署

本入口验证首页及现有教师申请流程。产品语言边界见[产品愿景](../product/vision.md)，技术限制见[架构](../architecture/overview.md)和[原 POC 手册](./recruitment-poc.md)。

## 边界与前置条件

- 使用当前 Issue 专属工作树及全新临时验证目录；需要 Node 24、pnpm 10.34.9、Docker Compose。按锁文件安装依赖。
- 默认不安装浏览器、运行库或系统依赖，不运行 Playwright 页面、交互或截图验收，CI 同样遵守。旧浏览器测试仅保留为历史回归入口，只有 owner 明确要求后才运行。
- 不读取共享 `.env`、员工密码，不运行共享 `poc.sh`、测试清库入口或共享 smoke。真实接口验证只使用本轮新建的专属数据库和合成账号。
- 每次外部副作用前运行任务提供的 `guard_command`，失败立即停止；commit、push、PR 前加 `--publish` 并立即操作。不要修改 guard、监听器、worker 状态/日志或其他工作树。

## 准备专属环境

将本轮受跟踪源码和新增 Issue 文件复制至新建的 `/tmp/voxnova-<execution-id>-<random>/`，排除 `.env`、密码、现有依赖、构建和测试产物。在该目录验证，避免复用共享资源。

在私密临时文件中准备 `VOXNOVA_TEST_RUN_ID`（唯一的小写字母、数字及短横线，最长 41 字符）、随机 `VOXNOVA_TEST_DB_PASSWORD`，及两个空闲回环端口 `VOXNOVA_TEST_API_PORT`、`VOXNOVA_TEST_WEB_PORT`。禁用 13080/13081/13082，不要打印密码。API 测试不启动网页服务器，web 端口只用于精确 Origin。

使用前检查同名项目、容器、网络、卷和 API 镜像不存在，确认端口空闲；占用即重新分配，不停止其他进程。专用配置 [compose.home-test.yaml](../../compose.home-test.yaml) 的数据库无宿主映射，只有 API 绑定 loopback，不连接业务代理网络。

## 类型、构建、格式和非浏览器验证

在专属源码副本中运行：

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend test:unit
pnpm --dir frontend typecheck
pnpm --dir frontend build
# 使用临时安装的固定 Prettier 3.6.2，检查本 Issue 改动文件。
```

`test:unit` 使用 Vue 内存渲染器执行真实页面 controller，并用 Vue 服务端渲染首页，不使用浏览器或 DOM 模拟器。覆盖文案键完整性、两种语言、首页区块删除、语言恢复及非法值/存储失败回退、标题/描述/lang、未保存内容保留、切换零请求、保存和提交请求、提示重新翻译、401 会话失效和员工强制中文。状态日期和错误映射、原始材料/员工记录保留同时验证。

## 专属真实 API 验证

每一步变更前运行 guard。下列命令中的 `TEST_ENV` 指本轮新建的 600 权限临时配置文件；schema 初始化仅允许用于本次全新空数据库，不用于升级已有数据库。

```bash
docker compose --env-file "$TEST_ENV" -f compose.home-test.yaml build api
docker compose --env-file "$TEST_ENV" -f compose.home-test.yaml up -d --wait db
docker compose --env-file "$TEST_ENV" -f compose.home-test.yaml run --rm --no-deps api uv run --frozen --no-dev python -m poc.cli init-db
docker compose --env-file "$TEST_ENV" -f compose.home-test.yaml up -d --no-build --wait api
# 只加载本轮新建配置；在运行这组接口写入前再次运行 guard。
set -a
. "$TEST_ENV"
set +a
pnpm --dir frontend test:api
```

验证健康、注册/登录/退出、密码与邮箱边界、必填/空白/最大字段长度、草稿创建/修改/读取、重复申请、无效版本、提交锁定、重新登录持久化、匿名拒绝、跨申请人不可见及员工接口拒绝。仅添加本轮合成数据，不删除既有资料。

CI 在全新的 GitHub runner 中保留类型、构建、Vue 非浏览器测试、真实 PostgreSQL 与 HTTP smoke；浏览器安装和运行步骤已移除。CI 中的原 POC 测试仅限该 runner 新建的数据资源，不能在本机既有业务服务执行。

## 验证结束与清理

先核对 `voxnova-home-$VOXNOVA_TEST_RUN_ID` 容器、默认网络和 `home-test-postgres` 卷的 Compose project 标签。guard 后只停止该轮项目：

```bash
docker compose --env-file "$TEST_ENV" -f compose.home-test.yaml stop
```

保留本轮合成测试卷、镜像和临时验证证据以便复核，不执行全局 prune。若以后决定删除测试数据，应重新核对归属并遵守当时的删除授权。本机结果同步记录 `/home/muise/MACHINE_MEMORY.md`，不含凭据。

## 更新既定服务及恢复

获批任务的常规 CI/CD 已由 owner 长期授权，无需另建部署 Issue 或逐步重新确认。新环境/付费资源、不可逆数据操作、权限或安全边界变化及业务决定仍须明确授权。

1. 先确认远端检查全部完成、PR/head/base 正确，构建使用 Git 精确提交的受跟踪文件。镜像标记完整 `org.opencontainers.image.revision`，保留旧镜像。
2. 只读核实既定环境 <https://careers.voxnova.cc/>、Compose 项目 `hl-pracitse-poc`、web/API/DB 资源、端口、网络和数据卷；记录更新前镜像和 API/DB 容器 ID。既定维护入口为 `/home/muise/.local/share/hl-pracitse-poc-runner/careers.sh`。
3. 准备当前前端镜像的固定版本覆盖文件、旧覆盖文件备份和恢复命令。只更新 web：使用既有基础 Compose、careers 覆盖和本轮固定镜像覆盖，执行 `up -d --no-deps --no-build --pull never --wait web`；不初始化、迁移、清库或重建 API/DB。
4. 验证镜像 revision、web healthy、本机和公网首页与 `/api/health` HTTP 200/ok，以及 API/DB ID、端口、网络和 proxy 别名保持一致。仅执行版本与基础 HTTP 检查，不进行浏览器页面验收。
5. 验证通过后更新 runner 的固定 web 镜像覆盖，确保维护入口继续指向该版本。操作前 guard，操作后回读。
6. 更新或健康检查失败时，以备份的旧镜像覆盖重建 web，再重复版本/健康及 API/DB 保留检查，恢复维护入口；保留失败和恢复证据。无需数据库恢复，不删除旧镜像、卷或已有数据。不把恢复准备写成已演练。
7. 交付精确提交、访问地址、CI、HTTP 和恢复证据，更新机器记忆及 PR，停在 In Review。

## owner 人工验收

在网站检查中文/English 首页、FAQ、注册登录、资料、保存、提交、状态和退出；确认指定页尾区块消失、其他申请入口和页脚正常。填写未保存内容后切换、刷新恢复语言，并从英文入口登录内部员工，确认管理界面及 AI 委托中文。重点检查 1440/390/320px 布局、英文换行、键盘与焦点、错误及校验提示。申请材料与员工自由填写记录保持原文。

上述页面和交互验收由 owner 完成；工程检查不代替人工验收。工程检查、CI、部署及基础健康完成后可交付 In Review，等待人验收不构成 Blocked，AI 不合并或标记 Done。
