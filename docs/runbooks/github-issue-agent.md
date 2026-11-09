# GitHub Issue 开发监听器

这是开发运维入口，不属于招聘业务接口。关联 Issue #4。继续采用人审核工作、AI 开发、人验收与合并的阶段 1 流程；每个 Issue 需要独立、明确的方案审批，不自动批准下一项工作。

## 日常使用

监听仓库 `houlinchn/hl-pracitse`，每 300 秒检查一次，只接受 `houlinchn` 创建的 Issue 和该账号的新评论。

1. 在 GitHub 选择“描述问题或需求”，只填写问题描述即可提交；标题已预填，期望结果和补充信息选填。工程信息由 Codex 在方案阶段补齐。启用后的新 Issue 自动进入只读方案讨论；旧 Issue 需要另发 `/codex plan` 才会接入。既有 POC #2 不自动重启开发。
2. 监听器回复方案，包含范围、验收、风险、依赖和文档影响。缺少业务决定时在同一 Issue 回复；它会重新调查并生成方案。
3. 完整方案末尾有类似 `/codex ready a12345678901` 的指令。复制该方案给出的完整指令，另发一条评论，即代表你授权这一版方案成为 Ready。单独说“ready”、修改看板或批准旧版本均不会启动开发。
4. 调度器记录授权评论链接，并将看板依次更新为 Ready / In Progress。在独立 worktree 单任务开发，不修改正在运行的 POC。
5. 本地验收通过后由调度器提交、推送并创建 PR，Issue 进入 In Review。PR 检查是否通过以 GitHub Checks 为准；自动交付不代表 CI 或人工验收已通过。
6. 验收意见继续在 Issue 评论，会重新讨论方案并要求新的 Ready 授权。最终合并、Done 和部署由人决定。

评论是公开操作记录，私密的 Codex 事件日志保存在服务器；不要在 Issue 中粘贴密码、令牌或个人资料。PR 评论不是本版监听入口。

| Issue 评论 | 行为 |
| --- | --- |
| `/codex plan` | 接入旧 Issue，或重新调查并生成方案 |
| `/codex ready 方案编号` | 仅批准最新且完整的一版方案，进入开发队列 |
| `/codex status` | 下一次轮询回复该 Issue 的监听状态 |
| `/codex pause` 或 `/codex stop` | 下一次轮询停止专属 worker，保留已有修改 |
| `/codex resume` | 从暂停恢复到方案讨论，需要重新批准 |
| `/codex retry` | 失败后重新调查；保留失败任务的修改，需要重新批准 |

指令必须独占评论，不识别引用块中的命令；编辑旧评论不会再次执行。正常情况下响应及暂停最长约 5 分钟；GitHub 网络故障时会延后。需求正文或标题变更、新的讨论意见会使旧方案失效，并停止正在执行的旧方案 worker。新增意见应保持在当前 Issue 范围内。

## 实现与运行边界

- 标准库 Python，`gh` 使用服务器现有 GitHub 登录，Codex 使用现有 CLI 登录和模型设置；没有新建 API 密钥。
- 用户级 systemd timer 每 300 秒启动一次短轮询；无任务时只查 GitHub，不调用模型。运行中的 worker 使用独立 systemd transient service，因此轮询仍能处理暂停。
- 单个进程锁保护轮询，持久化状态记录已处理评论、任务版本、授权和活动 worker；不会同时领取多个任务。
- 方案使用 read-only 沙箱，审批请求交给 automatic review；开发使用 `--approve-for-me` 的 workspace-write 沙箱，不绕过沙箱和审批。
- 模型只负责调查、修改及测试；调度器负责 GitHub 写入和代码交付。旧版本和关闭/暂停的 Issue 在创建 commit/PR 前再次校验。
- 每个任务最长 2 小时。异常或中断进入 Blocked，保留修改和私密日志，需要人工 `/codex retry`，不自动重试开发。服务重启后会核对活动 worker 与结果文件。
- GitHub 评论使用唯一标记防止自身触发和重复回复。源码安装到独立运行目录；开发 worktree 的修改不会立即改变监听器代码。
- 不自动合并、关闭 Issue、部署、修改线上容器或数据库；不复用共享 POC 的清库测试。需要这些操作时单独讨论并授权。
- 当前 main 可能尚未包含 POC #2；依赖 POC 的功能应先完成 #2 的人工验收与合并。批准时再次检查依赖和 main 版本。
- 本版不自动解释附件或截图、不处理第三方作者的 Issue/评论、不自动监控 PR CI 后修复、不对无结果的 worker 自动重启。

## 文件与安装

源码：`scripts/issue_agent/agent.py`。服务模板：同目录 `hl-issue-agent.service` / `.timer`。测试：`tests/test_issue_agent.py`。

本机运行目录 `/home/muise/.local/share/hl-pracitse-issue-agent/`，私密配置 `config.json`；状态及任务日志 `/home/muise/.local/state/hl-pracitse-issue-agent/`。目录 700、文件 600；配置不保存凭据。新任务工作树为 `/home/muise/wokrspace/hl-pracitse-issue-N`，分支 `codex/N-issue-agent`。

配置字段：`repo`、`owner`、`project`、`base`、`repo_dir`、`worktree_root`、`state_dir`、`gh`、`codex`、`git_email`、`path`、`since`、`excluded_issues`、`job_timeout`。`since` 是首次启用的 UTC 时间下界，不能在重启时重置；`excluded_issues` 包含本监听器交付 Issue #4 和已由人工会话领取的任务，避免重复处理。不要删除状态文件来“重试”，否则会失去去重和审批上下文。

部署前先确认 GitHub 身份、Codex 登录、用户级 systemd 和 `Linger=yes`。在批准的源码工作树执行：

```bash
python3 -m unittest discover -s tests -p 'test_issue_agent.py' -v
python3 -m py_compile scripts/issue_agent/agent.py
systemd-analyze --user verify scripts/issue_agent/hl-issue-agent.service scripts/issue_agent/hl-issue-agent.timer

# config.json 需按上述字段在本机准备；先停止轮询和正在运行的专属 worker，再更新代码。
install -d -m 700 /home/muise/.local/share/hl-pracitse-issue-agent
install -d -m 700 /home/muise/.local/state/hl-pracitse-issue-agent
install -d /home/muise/.config/systemd/user
install -m 600 scripts/issue_agent/agent.py /home/muise/.local/share/hl-pracitse-issue-agent/agent.py
install -m 644 scripts/issue_agent/hl-issue-agent.service /home/muise/.config/systemd/user/
install -m 644 scripts/issue_agent/hl-issue-agent.timer /home/muise/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start hl-issue-agent.service
systemctl --user enable --now hl-issue-agent.timer
```

首次启用前用只读 Codex 任务验证用户服务环境确实可读项目；不能仅凭进程启动就记为模型可用。不要在测试中伪造用户 Ready 评论以触发真实开发；审批逻辑使用隔离测试。

## 检查、停止与恢复

```bash
systemctl --user list-timers hl-issue-agent.timer
systemctl --user status hl-issue-agent.timer --no-pager
journalctl --user -u hl-issue-agent.service -n 40 --no-pager
python3 /home/muise/.local/share/hl-pracitse-issue-agent/agent.py status /home/muise/.local/share/hl-pracitse-issue-agent/config.json
systemctl --user list-units 'hl-issue-agent-job-*'

# 全局停止：同时关闭定时器、正在轮询的进程及所有本监听器 worker。
systemctl --user disable --now hl-issue-agent.timer
systemctl --user stop hl-issue-agent.service 'hl-issue-agent-job-*'

# 恢复：不删除状态，不自动重跑被中断任务。
systemctl --user enable --now hl-issue-agent.timer
```

回滚代码：在全局停止后，从已验收提交重新安装 `agent.py` 和单元文件，`daemon-reload` 后恢复 timer。保留状态、任务日志和工作树；清理前人工核对未提交/未推送修改。无需停止 POC、cc-connect 或其他服务。
