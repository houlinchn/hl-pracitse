# GitHub Issue 开发监听器

这是开发运维入口，不属于招聘业务接口。继续采用人审核工作、AI 开发、人验收与合并的阶段 1 流程；每个 Issue 需要独立的开发审批，不自动批准下一项工作。治理规则以 [开发规范](../development/vibe-coding.md) 为准。

## 分工与调用

```text
systemd 每 300 秒触发
→ 调度器读取 GitHub 事件、授权及状态，单任务排队
→ 独立 systemd worker 启动 codex exec，记录日志、超时和结果
→ Codex 理解讨论，执行当前授权范围的工作
→ 后续轮询由调度器校验结果、回写讨论及看板状态
```

- 调度器：身份校验、去重、队列、审批证据、任务租约、启停、结果校验和状态回写；不创建业务 Milestone、不替 Codex 提交代码或创建 PR，也不理解 message 里的交接请求。
- worker：启动并监控一次 Codex CLI 调用，保存私密日志和结构化结果；不分析需求、不执行 GitHub 或 Git 操作。
- Codex：阅读规范、理解需求、完成已明确获批的元数据操作；开发获批后实现、测试、更新文档、commit/push、创建或复用 PR，并按[常规工程交付](../development/vibe-coding.md#86-常规工程交付)完成 CI、既定环境部署、启动、运行验证和必要回退。无需单独批准部署，方案不重复提醒这些默认职责。禁止自行合并或标记 Done。

## 日常使用

仅监听仓库 `houlinchn/hl-pracitse`，仅接受 owner `houlinchn` 创建的 Issue 和该账号的直接评论。

1. 新 Issue 只需描述问题；启用后的新 Issue 自动调查，历史 Issue 用 `/codex plan` 接入。
2. Codex 读取带 ID 和链接的 owner 评论，区分确认、答疑和需求变更。已批准的 Milestone 创建、复用与关联由 Codex 直接执行并回读验证，不能仅返回“请调度器执行”。只有关联 Milestone 即可时不额外要求父 Issue。
3. 首次完整方案或范围发生变化时，调度器生成 `/codex ready 12位方案编号`。owner 独占一条新评论发送精确指令，才批准对应版本开发。普通“同意”只确认当前问题，不能批准开发或扩大授权。
4. 原方案没有改变的确认和答疑保留原方案编号及精确审批。运行中的任务会先停止副作用，再核对评论；确认原合同未变后可继续原授权，无需重复批准。
5. 新增业务决定或范围变化生成新方案并重新审批。权限不足、命令失败、已授权操作无法执行等返回 Blocked，保留证据，不再要求反复同意。阻塞解除后发 `/codex retry` 重新核对；不盲目重跑开发。
6. Codex 在专属 worktree 完成检查、commit/push 和 PR，自行跟进 GitHub Checks、修复本 Issue 引入的 CI 失败，并完成适用的部署和运行验收。无需再向人询问是否部署。调度器只校验 PR 的仓库、作者、base/head、代码版本及工作树状态后移到 In Review；CI 和运行证据由 Codex 提供，人最终验收、合并、Done。

| 评论 | 行为 |
| --- | --- |
| `/codex plan` | 接入旧 Issue，或重新核对讨论和方案 |
| `/codex ready 方案编号` | 仅批准最新完整方案，保存不可变合同和审批评论 |
| `/codex status` | 回复状态；不使执行中的任务失效 |
| `/codex pause` 或 `/codex stop` | 下一次轮询停止 worker；副作用前的 guard 会检查尚未轮询的新评论 |
| `/codex resume` | 恢复核对；仅原合同仍有效时继续原授权 |
| `/codex retry` | 核对阻塞是否解除，保留成果、合同和历史审批 |

指令必须独占评论，不从引用、附件或网页推断开发审批。编辑旧评论不作为新事件重放；guard 会检测正在执行的任务所依据的评论被编辑，已删除或修改的审批不能用于交付。需求正文或标题变化会停止旧任务并要求新方案。只监听 Issue 评论，不监听 PR 评论。

评论公开，完整事件日志私密；不要把凭据或个人资料贴到 Issue。同一个 GitHub 账号仍不能在技术上完全区分人工和 AI，最终人工门禁必须遵守。

## 结果与授权保存

Codex 返回 `message`、`outcome`、`risk`、`dependencies`、`pr_url`；非交付结果的 `pr_url` 留空。

| outcome | 处理 |
| --- | --- |
| ready | 保存新完整方案，等待新的精确 Ready 指令 |
| question | 等待一个未解决的业务决定；不延用旧合同开发 |
| blocked | 记录执行或依赖阻塞，不重新索要业务同意，不自动重试 |
| unchanged | 核对风险、依赖、正文和 base 均未变；保留方案编号，符合原审批时继续 |
| delivered | 读取并核验 Codex 已创建的 PR，停止于 In Review |

`plan` 保存当前方案，`approved_plan` 保存精确授权时的独立快照，`approval` 保存 owner 评论 ID、链接与方案编号。新讨论先核对合同，不立即删除历史授权；真正变更合同后旧批准只能作为审计证据。

版本 2 可以从旧状态中精确匹配的当前方案迁移批准合同。若旧方案已被覆盖，只能从本机原开发任务的输入中找回审批 ID、链接、token、正文摘要及仓库身份都匹配的合同；该记录先保持禁止执行，Codex 核对全部后续意见和已落实的前置步骤，确认原合同完全未变后才允许继续。缺少或不匹配的原合同不能仅凭旧 token 恢复开发。

## 副作用前检查与执行边界

任务资料包含本机 `guard_command`。Codex 每次执行 GitHub 写入或其他外部副作用前必须运行它；commit/push/PR 前加 `--publish`。guard 只读检查任务租约、身份、Issue 内容与开关、owner 评论 ID 和正文摘要；发布时还检查精确审批、依赖、base、当前分支、差异及私密文件。检查后立即执行操作；失败即停止，保留已完成动作的证据。

这些检查和提示约束不是任意命令的系统级隔离，不能消除检查与远端写入之间的竞态。暂停后不承诺撤销已经完成的远端操作；新任务必须先查事实并复用已有 Milestone、关联和 PR，避免重复。沙箱和 automatic review 继续启用，不使用危险绕过。

- 讨论任务使用 read-only 沙箱，不改项目文件；owner 已明确批准的 GitHub 元数据写入仍需通过正常命令审批。
- 开发任务使用 `--approve-for-me` 的 workspace-write；测试必须新建专属隔离环境，不运行共享 POC 清库入口。
- 每个任务最多 2 小时，systemd 使用 `KillMode=control-group`；暂停、关闭、中断、失败均保留日志和工作树。
- 修改 worktree 源码不会改变正在运行的安装版本。任务不得自行修改监听器、运行配置、租约、cc-connect 或其他工作树。
- 当前版本不解析附件；CI 检查和本 Issue 失败修复由 Codex 执行，调度器不代办。不自动合并或批准下一 Issue。

## 文件与验证

源码 `scripts/issue_agent/agent.py`；升级工具 `scripts/issue_agent/install.py`；服务模板在同目录；隔离测试 `tests/test_issue_agent.py`。

运行代码和私密配置 `/home/muise/.local/share/hl-pracitse-issue-agent/`；状态和日志 `/home/muise/.local/state/hl-pracitse-issue-agent/`。目录 700、私密文件 600。专属 worktree 为 `/home/muise/wokrspace/hl-pracitse-issue-N`，分支 `codex/N-issue-agent`。

配置字段保持原样：`repo`、`owner`、`project`、`base`、`repo_dir`、`worktree_root`、`state_dir`、`gh`、`codex`、`git_email`、`path`、`since`、`excluded_issues`、`job_timeout`。不能重置首次启用时间 `since`，不能删除状态来重试。

```bash
python3 -m unittest discover -s tests -p 'test_issue_agent.py' -v
python3 -m py_compile scripts/issue_agent/agent.py scripts/issue_agent/install.py
systemd-analyze --user verify scripts/issue_agent/hl-issue-agent.service scripts/issue_agent/hl-issue-agent.timer
```

测试不调用真实模型或 GitHub 写入，不伪造真实 owner 的 Ready 评论。真实模型对自然语言的判定和 GitHub 写入仍需在获授权的任务中验收。

## 现有安装升级与恢复

先确认本次变更已获人工批准、GitHub 身份与 Codex 登录正确、用户 systemd 可用，且无活动 worker。默认命令仅预演，不修改服务、代码、配置或状态：

```bash
python3 scripts/issue_agent/install.py
```

获准后添加 `--apply` 才真正升级。可选 `--exclude-issue` 指定由当前人工会话处理的维护 Issue，避免重复领取；`--reconcile` 指定一个已有 Issue 进入讨论核对，不伪造 Ready、不直接批准开发。不能同时排除并核对同一 Issue，也不能用此方式恢复暂停或已关闭任务。

升级工具停止 timer/poll 后加锁并再次检查活动任务；备份原 `agent.py`、`config.json`、`state.json` 至状态目录下私密 `backups/upgrade-*`；迁移状态并原子替换源码，最后只恢复原先正在运行的 timer。切换失败且新任务尚未启动时自动恢复该快照。不会启动招聘业务服务或修改数据库。`installation.json` 保存源码摘要和执行结果；实际运维和验证应记录于 MACHINE_MEMORY.md。

升级后回读源码摘要、timer 与真实轮询结果；不能以安装命令成功代替真实任务验收。版本 1 与版本 2 的任务结果不兼容，禁止在 worker 活动期间替换代码。

```bash
systemctl --user list-timers hl-issue-agent.timer
journalctl --user -u hl-issue-agent.service -n 40 --no-pager
python3 /home/muise/.local/share/hl-pracitse-issue-agent/agent.py status /home/muise/.local/share/hl-pracitse-issue-agent/config.json
systemctl --user list-units 'hl-issue-agent-job-*'
```

全局停止：

```bash
systemctl --user disable --now hl-issue-agent.timer
systemctl --user stop hl-issue-agent.service 'hl-issue-agent-job-*'
```

恢复 timer：

```bash
systemctl --user enable --now hl-issue-agent.timer
```

上线后回滚须先全局停止、检查新任务是否已产生远端写入，再从对应备份原子恢复代码和配置。状态和日志保留；只有明确确认备份后未执行任何新任务及外部操作，才可恢复旧状态快照。不能通过恢复旧状态重放已完成操作，也不删除工作树。无需停止招聘业务服务或 cc-connect。
