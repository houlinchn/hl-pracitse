# Voxnova 首页：隔离验收与部署交接

本入口验证首页及既有申请入口，不升级现有服务。产品能力与阶段以[产品愿景](../product/vision.md)为准，底层技术限制见[架构](../architecture/overview.md)和[原 POC 手册](./recruitment-poc.md)。

## 边界与前置条件

- 在当前 Issue 专属工作树操作；需要 Node 24、pnpm 10.34.9、Docker Compose 和 Playwright Chromium（含浏览器运行库、中文字体）。按锁文件安装前端依赖。
- 不读取现有 `.env`、员工密码或数据库配置，不运行共享 `poc.sh`、默认完整 E2E、清库或 smoke 脚本。
- `playwright.home.config.ts` 仅加载 `tests/home/`；所有浏览器 API 调用由合成 fixtures 明确处理，非站点请求被阻断，未声明的 API 使测试失败。独立 mock upstream 对漏过的请求返回 503，完全没有真实 API 回退路径。
- `playwright.home-fullstack.config.ts` 仅加载 `tests/home-fullstack/`，连接本次新建的 API。两个配置都禁止默认 POC 端口、复用已有 WebServer、trace 和 video。全栈只创建合成账号和申请，不创建员工或委托令牌。
- 受调度任务约束时，每次外部副作用前运行该任务提供的 `guard_command`，失败即停；commit、push、PR 前另加 `--publish` 并立即操作。下列每个 Docker 变更和测试启动均应单独执行 guard，不得用一次检查覆盖后续动作。

## 准备专属参数

在仓库根目录运行。每轮使用新的执行 ID；确认同名 Compose 项目、网络、卷和 API 镜像不存在，避免接管上轮资源。参数只写入本次临时私密目录，不打印密码。

```bash
umask 077
# 使用当前执行 ID，只能含小写字母、数字和短横线。
export VOXNOVA_TEST_RUN_ID=replace-with-current-run-id
export VOXNOVA_TEST_DIR="$(mktemp -d /tmp/voxnova-home.XXXXXX)"
python3 - <<'PY'
import os, re, secrets, socket
from pathlib import Path
run_id = os.environ['VOXNOVA_TEST_RUN_ID']
assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', run_id)
sockets = []
ports = []
for _ in range(3):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sockets.append(sock)
    ports.append(sock.getsockname()[1])
assert not set(ports) & {13080, 13081, 13082}
values = dict(zip(['VOXNOVA_TEST_WEB_PORT', 'VOXNOVA_TEST_API_PORT', 'VOXNOVA_TEST_MOCK_PORT'], map(str, ports)))
values.update(VOXNOVA_TEST_RUN_ID=run_id, VOXNOVA_TEST_DB_PASSWORD=secrets.token_hex(32))
Path(os.environ['VOXNOVA_TEST_DIR'], 'test.env').write_text(''.join(f'{key}={value}\n' for key, value in values.items()))
PY
# 此处仅加载上一步新建的配置，绝不加载仓库 .env。
set -a
. "$VOXNOVA_TEST_DIR/test.env"
set +a
docker compose ls
docker network ls --filter "label=com.docker.compose.project=voxnova-home-$VOXNOVA_TEST_RUN_ID"
docker volume ls --filter "label=com.docker.compose.project=voxnova-home-$VOXNOVA_TEST_RUN_ID"
```

端口分配后仍须在启动前复核空闲；占用即重新准备，不停止其他进程。Compose 使用显式临时 env 文件和独立配置，不加载默认 `compose.yaml`。数据库不映射宿主端口，只加入本次项目私有网络；API 仅绑定 loopback。配置中的 `APP_ORIGIN` 与浏览器端口必须一致，不能给全栈测试临时换一个前端端口。

## 类型、构建与模拟页面测试

```bash
pnpm --dir frontend typecheck
pnpm --dir frontend build
pnpm --dir frontend exec playwright test --config playwright.home.config.ts
```

覆盖 1440、390、320px；检查品牌和元信息、锚点导航、FAQ、注册与登录入口、键盘焦点、弹窗约束/关闭/焦点恢复、首次加载和认证失败，以及申请人、员工详情和委托页面的正常、失败、无权限与窄屏布局。这些是模拟资料的前端验证，不代替真实权限或审计验收。

首页审查示例：[1440px](../assets/voxnova-home/home-1440.png)、[390px](../assets/voxnova-home/home-390.png)、[320px](../assets/voxnova-home/home-320.png)。最终视觉效果由 owner 验收。

截图写入 `frontend/test-results/home/`（不入库，权限由 077 umask 保护）。首页无个人资料，可将三张 `homepage.png` 单独复制到审查附件；工作台截图仅含合成资料，不截取令牌。

## 专属全栈测试

每步前核验 guard。下面的 schema 初始化只允许对本次新建的空数据库执行；绝不能用于升级已有数据库。

```bash
docker compose --env-file "$VOXNOVA_TEST_DIR/test.env" -f compose.home-test.yaml build api
docker compose --env-file "$VOXNOVA_TEST_DIR/test.env" -f compose.home-test.yaml up -d --wait db
docker compose --env-file "$VOXNOVA_TEST_DIR/test.env" -f compose.home-test.yaml run --rm --no-deps api uv run --frozen --no-dev python -m poc.cli init-db
docker compose --env-file "$VOXNOVA_TEST_DIR/test.env" -f compose.home-test.yaml up -d --no-build --wait api
pnpm --dir frontend exec playwright test --config playwright.home-fullstack.config.ts
```

模拟测试结束并释放前端端口后再运行全栈配置。验证真实健康检查、浏览器注册、草稿创建和修改、刷新后持久化、提交锁定、重新登录、申请人访问员工接口被拒绝、未登录请求被拒绝。截图位于 `frontend/test-results/home-fullstack/`，只含本轮合成资料。此测试不声明已经验证完整员工/AI 业务链路；该链路的稳定规则和原测试保持不变。

## 验收结束与恢复

先等待 Playwright 退出，其 WebServer 自动停止。若测试异常中断，只停止核对过 PID、命令和端口的本轮进程。核对资源归属后，清理本次全新项目（以下会删除本轮合成数据）：

```bash
docker volume inspect "voxnova-home-${VOXNOVA_TEST_RUN_ID}_home-test-postgres" --format '{{json .Labels}}'
docker network inspect "voxnova-home-${VOXNOVA_TEST_RUN_ID}_default" --format '{{json .Labels}}'
# 确认标签中的 project、资源名称与本轮完全一致，并运行 guard 后：
docker compose --env-file "$VOXNOVA_TEST_DIR/test.env" -f compose.home-test.yaml down --volumes
```

不使用全局 prune，不删除其他环境资源。单独的本轮 API 镜像和工具可以保留作复核，不包含已有业务数据。临时凭据只供该已清理数据库，不能复制到运行服务。本机操作结果和清理状态同步记入 `/home/muise/MACHINE_MEMORY.md`，不记录凭据。

## 现有服务部署交接

首页可通过恢复部署前代码版本回退，不涉及表结构迁移。当前方案仅授权开发和新建隔离验收环境，现有运行服务保持原样。独立部署任务须给出并核验：

1. 明确的目标环境、域名/访问入口、项目和前后端资源归属；需要更新的组件及保留的数据边界。
2. 已验收 PR 的精确提交和构建版本，部署前可恢复的原版本和必要备份。
3. 更新和启动步骤、运行健康检查、首页品牌/静态资源及登录申请入口的验证方法。
4. 触发恢复的条件、恢复原代码/镜像步骤和恢复后验证。
5. 可核验的 owner 授权，以及最终访问地址、版本、健康状态和恢复证据。

这些运行证据齐备之前，服务运行验收保持待完成；本地构建、隔离测试或 PR 都不能替代现有网站运行证据。人工重点检查三种视口的视觉效果、中文文案、岗位信息准确性、键盘体验和原网站的最终部署版本。
