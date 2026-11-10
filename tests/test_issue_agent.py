"""Authorization, cancellation, recovery and publication tests; no real API/model."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "agent", Path(__file__).parents[1] / "scripts/issue_agent/agent.py"
)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def issue(number=10, owner="houlinchn", created="2026-11-10T12:00:00Z"):
    return {
        "number": number,
        "title": "Improve UI",
        "body": "Explicit request",
        "state": "open",
        "created_at": created,
        "user": {"login": owner},
        "html_url": f"https://github.com/houlinchn/hl-pracitse/issues/{number}",
    }


def comment(body, cid=1, owner="houlinchn"):
    return {
        "body": body,
        "id": cid,
        "user": {"login": owner},
        "created_at": "2026-11-10T12:10:00Z",
        "html_url": f"https://github.com/houlinchn/hl-pracitse/issues/10#issuecomment-{cid}",
    }


def reviewed():
    return {
        "mode": "human_review",
        "generation": 1,
        "seen": [],
        "digest": agent.digest(issue()),
        "plan": {
            "ready": True,
            "token": "a12345678901",
            "digest": agent.digest(issue()),
            "main_sha": "main1",
            "risk": "L1",
            "message": "Approved UI contract",
            "dependencies": [],
        },
    }


class FakeGitHub:
    def __init__(self, issues=None):
        self.items = issues or []
        self.cs = {}
        self.posts = {}
        self.statuses = []

    def api(self, endpoint, *args, **kwargs):
        assert endpoint == "user"
        return {"login": "houlinchn"}

    def issues(self):
        return copy.deepcopy(self.items)

    def issue(self, number):
        return copy.deepcopy(next(i for i in self.items if i["number"] == number))

    def comments(self, number):
        return copy.deepcopy(self.cs.get(number, []))

    def post(self, number, key, message):
        self.posts.setdefault((number, key), message)

    def status(self, number, value):
        self.statuses.append((number, value))


class ApprovalTests(unittest.TestCase):
    def test_exact_current_plan_only(self):
        s = reviewed()
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        self.assertEqual(s["mode"], "approved")
        self.assertEqual(s["approval"]["id"], 1)

    def test_stale_wrong_and_missing_tokens_are_rejected(self):
        for body in ("/codex ready", "/codex ready b12345678901", "ready", "可以开始开发"):
            s = reviewed()
            agent.apply_comment(s, comment(body), issue())
            self.assertNotEqual(s["mode"], "approved")

    def test_issue_edit_revokes_approval(self):
        s, edited = reviewed(), issue()
        edited["body"] += " expanded scope"
        agent.apply_comment(s, comment("/codex ready a12345678901"), edited)
        self.assertEqual(s["mode"], "human_review")

    def test_unresolved_plan_cannot_be_approved(self):
        s = reviewed()
        s["plan"]["ready"] = False
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        self.assertEqual(s["mode"], "human_review")

    def test_owner_only_and_no_replays_or_self_comments(self):
        s = reviewed()
        s["seen"] = [2]
        cs = [
            comment("/codex ready a12345678901", 1, "stranger"),
            comment("/codex plan", 2),
            comment(agent.MARKER + "test -->", 3),
            comment("/codex plan", 4),
        ]
        cfg = {"owner": "houlinchn"}
        self.assertEqual([c["id"] for c in agent.incoming(issue(), cs, s, cfg, "2026-11-10")], [4])
        self.assertEqual(agent.incoming(issue(owner="stranger"), cs, s, cfg, "2026-11-10"), [])

    def test_discussion_stops_execution_but_preserves_approved_snapshot(self):
        s = reviewed()
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        agent.apply_comment(s, comment("Also change permissions", 2), issue())
        self.assertEqual(s["mode"], "plan_pending")
        self.assertEqual(s["generation"], 2)
        self.assertEqual(s["approved_plan"]["token"], "a12345678901")

    def test_pause_resume_needs_fresh_plan(self):
        s = reviewed()
        agent.apply_comment(s, comment("/codex pause"), issue())
        agent.apply_comment(s, comment("casual discussion", 2), issue())
        self.assertEqual(s["mode"], "paused")
        agent.apply_comment(s, comment("/codex resume", 3), issue())
        self.assertEqual(s["mode"], "plan_pending")

    def test_public_reply_rejects_secret_before_post(self):
        gh = agent.GitHub({"owner": "houlinchn", "repo": "example/repo"})
        with patch.object(gh, "api") as api, self.assertRaises(RuntimeError):
            gh.post(10, "key", "ghp_" + "x" * 36)
        api.assert_not_called()

    def test_comment_post_recovers_after_lost_response(self):
        gh = agent.GitHub({"owner": "houlinchn", "repo": "example/repo"})
        existing = comment("Already posted\n" + agent.MARKER + "job1 -->")
        with patch.object(gh, "comments", return_value=[existing]), patch.object(gh, "api") as api:
            self.assertEqual(gh.post(10, "job1", "Already posted"), existing)
        api.assert_not_called()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = {
            "state_dir": self.temp.name,
            "owner": "houlinchn",
            "since": "2026-11-10T00:00:00Z",
            "excluded_issues": [4],
            "repo": "houlinchn/hl-pracitse",
        }
        self.gh = FakeGitHub()
        self.e = agent.Engine(self.cfg, self.gh)

    def test_historical_issue_and_tracker_never_autostart(self):
        self.gh.items = [
            issue(2, created="2026-11-08T00:00:00Z"),
            issue(4),
            issue(11, owner="stranger"),
        ]
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(self.e.state["issues"]["2"]["mode"], "ignored")
        self.assertNotIn("4", self.e.state["issues"])

    def test_new_issue_plans_without_developing(self):
        self.gh.items = [issue()]
        with patch.object(self.e, "start") as start:
            self.e.poll()
        self.assertEqual(start.call_args.args[-1], "plan")

    def test_one_task_per_poll(self):
        self.gh.items = [issue(10), issue(11)]
        with patch.object(self.e, "start") as start:
            self.e.poll()
        self.assertEqual(start.call_count, 1)

    def test_posted_command_is_not_replayed_after_restart(self):
        self.gh.items = [issue()]
        self.gh.cs[10] = [comment("/codex status")]
        self.e.state["issues"]["10"] = reviewed()
        self.e.poll()
        restarted = agent.Engine(self.cfg, self.gh)
        self.assertEqual(
            agent.incoming(
                issue(),
                self.gh.cs[10],
                restarted.state["issues"]["10"],
                self.cfg,
                self.cfg["since"],
            ),
            [],
        )

    def active(self, kind="develop"):
        a = {
            "id": "job1",
            "unit": "test-unit",
            "number": 10,
            "kind": kind,
            "generation": 1,
            "digest": agent.digest(issue()),
            "main_sha": "main1",
            "worktree": "/unused",
            "branch": "codex/10-issue-agent",
        }
        self.e.state.update(active=a, issues={"10": reviewed()})
        if kind == "develop":
            agent.apply_comment(
                self.e.state["issues"]["10"], comment("/codex ready a12345678901", 0), issue()
            )
        self.e.state["issues"]["10"]["mode"] = "developing" if kind == "develop" else "planning"
        self.gh.items = [issue()]
        return a

    def result(self, ready=True):
        agent.atomic(
            Path(self.temp.name) / "jobs/job1/result.json",
            {
                "ok": True,
                "answer": {
                    "outcome": (
                        "ready" if self.e.state["active"]["kind"] == "plan" else "delivered"
                    )
                    if ready
                    else "blocked",
                    "message": "Verified",
                    "risk": "L1",
                    "dependencies": [],
                    "pr_url": "https://github.com/houlinchn/hl-pracitse/pull/12" if ready else "",
                },
            },
        )

    @patch.object(agent.subprocess, "run")
    def test_pause_wins_over_finished_result(self, proc):
        self.active()
        self.result()
        self.gh.cs[10] = [comment("/codex pause")]
        with patch.object(self.e, "verify_delivery") as publish:
            self.e.poll()
        publish.assert_not_called()
        proc.assert_called_once()
        self.assertIsNone(self.e.state["active"])
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "paused")

    @patch.object(agent.subprocess, "run")
    def test_closed_issue_cancels_worker(self, proc):
        self.active()
        self.result()
        self.gh.items = []
        with patch.object(self.e, "verify_delivery") as publish:
            self.e.poll()
        publish.assert_not_called()
        proc.assert_called_once()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "closed")

    def test_changed_body_wins_over_finished_result(self):
        self.active()
        self.result()
        self.gh.items[0]["body"] += " changed"
        with (
            patch.object(agent.subprocess, "run"),
            patch.object(self.e, "verify_delivery") as publish,
            patch.object(self.e, "start") as start,
        ):
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(start.call_args.args[-1], "discuss")

    def test_plan_does_not_publish_code(self):
        self.active("plan")
        self.result()
        with patch.object(self.e, "verify_delivery") as publish:
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "human_review")
        self.assertIn("/codex ready job1", self.gh.posts[(10, "result-job1")])

    def test_success_delivers_and_stops_in_review(self):
        self.active()
        self.result()
        with patch.object(
            self.e, "verify_delivery", return_value="https://example.com/pr"
        ) as publish:
            self.e.poll()
        publish.assert_called_once()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "in_review")
        self.assertIn((10, "In Review"), self.gh.statuses)
        self.assertIsNone(self.e.state["active"])

    @patch.object(agent.subprocess, "run")
    def test_interrupted_job_does_not_retry_implementation(self, proc):
        self.active()
        proc.return_value.stdout = "inactive\n"
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "blocked")

    @patch.object(agent.subprocess, "run")
    def test_failed_acceptance_never_publishes(self, proc):
        self.active()
        self.result(ready=False)
        with patch.object(self.e, "verify_delivery") as publish:
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "blocked")

    def test_open_dependency_prevents_worker_launch(self):
        self.gh.items = [issue(10), issue(2)]
        s = reviewed()
        s["plan"]["dependencies"] = [2]
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        self.cfg.update(repo_dir="/unused", base="main")
        with (
            patch.object(self.e, "worktree", return_value=(Path("/unused"), "test")),
            patch.object(self.e, "git", return_value="main1"),
            patch.object(agent, "run") as run,
            self.assertRaisesRegex(RuntimeError, "Dependency #2"),
        ):
            self.e.start(issue(), s, "develop")
        run.assert_not_called()

    def test_changed_main_prevents_worker_launch(self):
        self.gh.items = [issue()]
        self.cfg.update(repo_dir="/unused", base="main")
        with (
            patch.object(self.e, "worktree", return_value=(Path("/unused"), "test")),
            patch.object(self.e, "git", return_value="main2"),
            patch.object(agent, "run") as run,
            self.assertRaisesRegex(RuntimeError, "base branch changed"),
        ):
            s = reviewed()
            agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
            self.e.start(issue(), s, "develop")
        run.assert_not_called()

    def test_launch_passes_traceable_contract_and_guard_to_codex(self):
        self.gh.items = [issue()]
        self.gh.cs[10] = [
            comment("/codex ready a12345678901"),
            comment("stranger", 2, "stranger"),
            comment("/codex status", 3),
        ]
        s = reviewed()
        agent.apply_comment(s, self.gh.cs[10][0], issue())
        self.e.state["issues"]["10"] = s
        self.cfg.update(repo_dir="/unused", path="/usr/bin", git_email="test@example.com")
        with (
            patch.object(
                self.e, "worktree", return_value=(Path("/unused"), "codex/10-issue-agent")
            ),
            patch.object(self.e, "git", return_value="main1"),
            patch.object(agent, "run") as run,
        ):
            self.e.start(issue(), s, "develop")
        launch = run.call_args.args[0]
        self.assertEqual(launch[0], "systemd-run")
        self.assertIn("--property=KillMode=control-group", launch)
        job = json.loads(Path(launch[-1]).read_text())
        context = json.loads(job["prompt"].split("\n任务资料 JSON：\n", 1)[1])
        self.assertEqual([c["id"] for c in context["owner_comments"]], [1, 3])
        self.assertEqual(context["owner_comments"][0]["url"], self.gh.cs[10][0]["html_url"])
        self.assertEqual(context["approved_plan"]["token"], "a12345678901")
        self.assertEqual(context["guard_command"][-1], launch[-1])
        self.assertEqual(job["comment_receipts"], agent.comment_receipts([self.gh.cs[10][0]]))
        self.assertEqual(s["mode"], "developing")

    def test_removed_approval_cannot_start_development(self):
        self.gh.items = [issue()]
        s = reviewed()
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        self.cfg.update(repo_dir="/unused", path="/usr/bin")
        with (
            patch.object(self.e, "worktree", return_value=(Path("/unused"), "test")),
            patch.object(self.e, "git", return_value="main1"),
            patch.object(agent, "run") as run,
            self.assertRaisesRegex(RuntimeError, "edited or removed"),
        ):
            self.e.start(issue(), s, "develop")
        run.assert_not_called()
        self.assertEqual(self.gh.statuses, [])

    def test_state_is_reloaded_after_acquiring_poll_lock(self):
        config = Path(self.temp.name) / "config.json"
        agent.atomic(config, self.cfg)
        self.e.save()

        def acquire(*args):
            changed = copy.deepcopy(self.e.state)
            changed["committed_by_previous_poll"] = True
            agent.atomic(self.e.file, changed)

        observed = []

        def poll(engine):
            observed.append(engine.state.get("committed_by_previous_poll"))
            engine.state["last_poll"] = agent.now()

        with (
            patch.object(sys, "argv", ["agent.py", "poll", str(config)]),
            patch.object(agent.fcntl, "flock", side_effect=acquire),
            patch.object(agent.Engine, "poll", new=poll),
            patch("builtins.print"),
        ):
            agent.main()
        self.assertEqual(observed, [True])


class ConversationTests(unittest.TestCase):
    setUp = EngineTests.setUp
    active = EngineTests.active
    result = EngineTests.result

    def discussion(self, outcome, authorized=False, **changes):
        a = self.active("plan")
        s = self.e.state["issues"]["10"]
        if authorized:
            s["mode"] = "human_review"
            agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        agent.apply_comment(s, comment("同意，你创建并关联 Milestone", 2), issue())
        a["generation"] = s["generation"]
        a["kind"] = "discuss"
        s["mode"] = "planning"
        answer = {
            "outcome": outcome,
            "message": "Verified decision",
            "risk": "L1",
            "dependencies": [],
            "pr_url": "",
        }
        answer.update(changes)
        agent.atomic(Path(self.temp.name) / "jobs/job1/result.json", {"ok": True, "answer": answer})
        return s

    def test_confirmation_preserves_approval_and_resumes_same_contract(self):
        s = self.discussion("unchanged", authorized=True)
        original = copy.deepcopy(s["approved_plan"])
        with patch.object(self.e, "start") as start:
            self.e.poll()
        self.assertEqual(start.call_args.args[-1], "develop")
        self.assertEqual(s["approved_plan"], original)
        self.assertEqual(s["plan"]["token"], "a12345678901")
        self.assertNotIn("/codex ready job1", self.gh.posts[(10, "result-job1")])

    def test_unapproved_confirmation_keeps_same_ready_token_without_developing(self):
        s = self.discussion("unchanged")
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["mode"], "human_review")
        self.assertEqual(s["plan"]["token"], "a12345678901")
        self.assertNotIn("approved_plan", s)

    def test_blocker_keeps_approval_but_does_not_request_reapproval_or_autoretry(self):
        s = self.discussion("blocked", authorized=True)
        with patch.object(self.e, "start") as start:
            self.e.poll()
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["mode"], "blocked")
        self.assertEqual(s["approval"]["plan"], "a12345678901")
        self.assertIn("无需重复同意", self.gh.posts[(10, "result-job1")])
        self.assertNotIn((10, "Human Review"), self.gh.statuses)

    def test_business_question_revokes_execution_not_historical_evidence(self):
        s = self.discussion("question", authorized=True)
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["mode"], "awaiting_input")
        self.assertFalse(agent.approved(s, issue(), "main1"))
        self.assertIn("approved_plan", s)

    def test_new_contract_requires_fresh_exact_approval(self):
        s = self.discussion("ready", authorized=True, risk="L2")
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["plan"]["token"], "job1")
        self.assertFalse(agent.approved(s, issue(), "main1"))
        self.assertEqual(s["approved_plan"]["risk"], "L1")

    def test_new_plan_cannot_silently_lower_risk(self):
        s = self.discussion("ready", authorized=True, risk="L0")
        with patch.object(agent.subprocess, "run"), patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["mode"], "blocked")
        self.assertIn("Risk cannot be lowered", self.gh.posts[(10, "failure-job1")])

    def test_unchanged_cannot_raise_risk_or_dependencies(self):
        for change in ({"risk": "L2"}, {"dependencies": [2]}):
            with self.subTest(change=change):
                s = self.discussion("unchanged", authorized=True, **change)
                with patch.object(agent.subprocess, "run"), patch.object(self.e, "start") as start:
                    self.e.poll()
                start.assert_not_called()
                self.assertEqual(s["mode"], "blocked")

    def test_changed_base_or_body_cannot_resume_old_contract(self):
        for field in ("main_sha", "digest"):
            s = self.discussion("unchanged", authorized=True)
            s["plan"][field] = "old"
            with patch.object(agent.subprocess, "run"), patch.object(self.e, "start") as start:
                self.e.poll()
            start.assert_not_called()
            self.assertEqual(s["mode"], "blocked")

    def test_completed_contract_acknowledgement_does_not_reopen_development(self):
        s = self.discussion("unchanged", authorized=True)
        s.update(
            pr="https://github.com/houlinchn/hl-pracitse/pull/12", delivered_plan="a12345678901"
        )
        with patch.object(self.e, "start") as start:
            self.e.poll()
        start.assert_not_called()
        self.assertEqual(s["mode"], "in_review")

    def test_unrelated_previous_pr_does_not_suppress_approved_update(self):
        s = self.discussion("unchanged", authorized=True)
        s.update(pr="https://github.com/houlinchn/hl-pracitse/pull/12", delivered_plan="older")
        with patch.object(self.e, "start") as start:
            self.e.poll()
        self.assertEqual(start.call_args.args[-1], "develop")

    def test_legacy_approval_migrates_only_when_exact_plan_is_available(self):
        for token, expected in (("a12345678901", True), ("older", False)):
            s = reviewed()
            s["approval"] = {"plan": token, "id": 1, "url": "evidence"}
            self.e.state["issues"]["10"] = s
            self.e.save()
            migrated = agent.Engine(self.cfg, self.gh).state["issues"]["10"]
            self.assertEqual("approved_plan" in migrated, expected)
        self.assertEqual(agent.Engine(self.cfg, self.gh).state["version"], 2)


class LegacyArchiveTests(unittest.TestCase):
    def test_exact_original_job_is_recovered_but_not_automatically_authorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "state_dir": tmp,
                "repo": "houlinchn/hl-pracitse",
                "owner": "houlinchn",
                "since": "2026-11-10",
            }
            original = reviewed()["plan"]
            authority = {"id": 1, "url": "evidence", "plan": original["token"]}
            current = reviewed()
            current.update(plan={**original, "ready": False, "token": "later"}, approval=authority)
            agent.atomic(Path(tmp) / "state.json", {"issues": {"10": current}, "active": None})
            context = {"approved_plan": original, "approval": authority}
            job = {
                "kind": "develop",
                "number": 10,
                "cfg": cfg,
                "prompt": "rules\n任务资料 JSON：\n" + json.dumps(context),
            }
            agent.atomic(Path(tmp) / "jobs/original/job.json", job)
            e = agent.Engine(cfg, FakeGitHub())
            s = e.state["issues"]["10"]
            self.assertEqual(s["approved_plan"], original)
            self.assertTrue(s["legacy_revalidation"])
            self.assertFalse(agent.approved(s, issue(), "main1"))
            a = {
                "id": "reconcile",
                "number": 10,
                "digest": agent.digest(issue()),
                "main_sha": "main1",
            }
            answer = {
                "outcome": "unchanged",
                "message": "All subsequent comments preserve original scope",
                "risk": "L1",
                "dependencies": [],
                "pr_url": "",
            }
            e.finish_discussion(a, s, issue(), answer)
            self.assertTrue(agent.approved(s, issue(), "main1"))
            self.assertEqual(s["plan"]["token"], original["token"])
            self.assertEqual(s["mode"], "approved")

    def test_archive_with_wrong_approval_or_repository_is_not_recovered(self):
        for change in ("authority", "repository", "malformed"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                cfg = {
                    "state_dir": tmp,
                    "repo": "houlinchn/hl-pracitse",
                    "owner": "houlinchn",
                    "since": "2026-11-10",
                }
                original = reviewed()["plan"]
                authority = {"id": 1, "url": "evidence", "plan": original["token"]}
                current = reviewed()
                current.update(plan={**original, "token": "later"}, approval=authority)
                agent.atomic(Path(tmp) / "state.json", {"issues": {"10": current}, "active": None})
                context = {
                    "approved_plan": original,
                    "approval": {**authority, "id": 2} if change == "authority" else authority,
                }
                job = {
                    "kind": "develop",
                    "number": 10,
                    "cfg": {**cfg, "repo": "stranger/repo"} if change == "repository" else cfg,
                    "prompt": "malformed"
                    if change == "malformed"
                    else "rules\n任务资料 JSON：\n" + json.dumps(context),
                }
                agent.atomic(Path(tmp) / "jobs/original/job.json", job)
                self.assertNotIn(
                    "approved_plan", agent.Engine(cfg, FakeGitHub()).state["issues"]["10"]
                )


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = {
            "state_dir": str(self.root),
            "repo": "houlinchn/hl-pracitse",
            "owner": "houlinchn",
        }
        s = reviewed()
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        s["mode"] = "developing"
        self.state = {"active": {"id": "job1"}, "issues": {"10": s}}
        self.job = {
            "id": "job1",
            "cfg": self.cfg,
            "number": 10,
            "generation": 1,
            "digest": agent.digest(issue()),
            "kind": "develop",
            "main_sha": "main1",
            "worktree": str(self.root / "work"),
            "branch": "codex/10-issue-agent",
            "comment_ids": [1],
        }
        self.gh = FakeGitHub([issue()])
        self.gh.cs[10] = [comment("/codex ready a12345678901")]
        self.job["comment_receipts"] = agent.comment_receipts(self.gh.cs[10])

        def api(endpoint):
            if endpoint == "user":
                return {"login": "houlinchn"}
            return {"object": {"sha": "main1"}}

        self.gh.api = api
        self.client = patch.object(agent, "GitHub", return_value=self.gh)
        self.client.start()
        self.addCleanup(self.client.stop)

    def save(self):
        agent.atomic(self.root / "state.json", self.state)

    def test_current_metadata_and_publish_lease(self):
        self.save()
        agent.guard(self.job)
        with (
            patch.object(agent, "run", return_value=self.job["branch"]),
            patch.object(agent, "check_files") as files,
        ):
            agent.guard(self.job, publish=True)
        files.assert_called_once_with(self.job["worktree"], "main1")

    def test_pause_close_generation_and_other_job_revoke_lease(self):
        for mode in ("paused", "closed", "blocked", "plan_pending"):
            self.state["issues"]["10"]["mode"] = mode
            self.save()
            with self.assertRaisesRegex(RuntimeError, "lease"):
                agent.guard(self.job)
        self.state["issues"]["10"].update(mode="developing", generation=2)
        self.save()
        with self.assertRaisesRegex(RuntimeError, "lease"):
            agent.guard(self.job)
        self.state["issues"]["10"]["generation"] = 1
        self.state["active"]["id"] = "other"
        self.save()
        with self.assertRaisesRegex(RuntimeError, "lease"):
            agent.guard(self.job)

    def test_new_owner_comment_blocks_writes_before_next_poll(self):
        self.save()
        self.gh.cs[10].append(comment("/codex pause", 2))
        with self.assertRaisesRegex(RuntimeError, "discussion changed"):
            agent.guard(self.job)

    def test_status_third_party_and_agent_comments_do_not_revoke_lease(self):
        self.save()
        self.gh.cs[10] += [
            comment("/codex status", 2),
            comment("change scope", 3, "stranger"),
            comment(agent.MARKER + "result -->", 4),
        ]
        agent.guard(self.job)

    def test_editing_owner_comment_revokes_metadata_lease(self):
        self.save()
        self.gh.cs[10][0]["body"] = "different authority with same comment ID"
        with self.assertRaisesRegex(RuntimeError, "discussion changed"):
            agent.guard(self.job)

    def test_changed_issue_or_closed_issue_blocks_writes(self):
        self.save()
        for change in ({"state": "closed"}, {"body": "changed"}):
            self.gh.items = [{**issue(), **change}]
            with self.assertRaisesRegex(RuntimeError, "changed or closed"):
                agent.guard(self.job)

    def test_wrong_identity_blocks_even_metadata(self):
        self.save()
        self.gh.api = lambda endpoint: {"login": "stranger"}
        with self.assertRaisesRegex(RuntimeError, "identity"):
            agent.guard(self.job)

    def test_planning_cannot_publish_and_edited_approval_cannot_publish(self):
        self.save()
        self.job["kind"] = "plan"
        with self.assertRaisesRegex(RuntimeError, "authorization"):
            agent.guard(self.job, publish=True)
        self.job["kind"] = "develop"
        self.gh.cs[10][0]["body"] = "edited away"
        self.job["comment_receipts"] = agent.comment_receipts(self.gh.cs[10])
        with self.assertRaisesRegex(RuntimeError, "edited or removed"):
            agent.guard(self.job, publish=True)

    def test_reopened_dependency_and_changed_main_block_delivery(self):
        self.state["issues"]["10"]["approved_plan"]["dependencies"] = [2]
        self.gh.items.append(issue(2))
        self.save()
        with self.assertRaisesRegex(RuntimeError, "Dependency reopened"):
            agent.guard(self.job, publish=True)
        self.gh.items[1]["state"] = "closed"
        self.gh.api = lambda endpoint: (
            {"login": "houlinchn"} if endpoint == "user" else {"object": {"sha": "newmain"}}
        )
        with self.assertRaisesRegex(RuntimeError, "Base branch changed"):
            agent.guard(self.job, publish=True)


class WorkerTests(unittest.TestCase):
    def test_worker_launches_only_and_collects_structured_result(self):
        for kind in ("plan", "discuss", "develop"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                job = {
                    "kind": kind,
                    "cfg": {"codex": "fake-codex", "job_timeout": 17},
                    "worktree": tmp,
                    "prompt": "task",
                }
                agent.atomic(root / "job.json", job)
                answer = {
                    "outcome": "blocked",
                    "message": "No external calls",
                    "risk": "L1",
                    "dependencies": [],
                    "pr_url": "",
                }

                def launch(args, kind=kind, root=root, answer=answer, **kwargs):
                    self.assertEqual(args[0:2], ["fake-codex", "exec"])
                    self.assertEqual(kwargs["timeout"], 17)
                    self.assertEqual(kwargs["input"], "task")
                    self.assertEqual("--approve-for-me" in args, kind == "develop")
                    self.assertEqual("read-only" in args, kind != "develop")
                    agent.atomic(root / "answer.json", answer)
                    return subprocess.CompletedProcess(args, 0)

                with patch.object(agent.subprocess, "run", side_effect=launch):
                    agent.worker(root / "job.json")
                result = json.loads((root / "result.json").read_text())
                self.assertTrue(result["ok"])
                self.assertEqual(result["answer"], answer)

    def test_timeout_or_invalid_result_is_recorded_without_retry(self):
        for failure in (subprocess.TimeoutExpired("fake-codex", 1), None):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                agent.atomic(
                    root / "job.json",
                    {
                        "kind": "develop",
                        "cfg": {"codex": "fake"},
                        "worktree": tmp,
                        "prompt": "task",
                    },
                )
                agent.atomic(root / "answer.json", {"ready": True})
                with (
                    patch.object(
                        agent.subprocess,
                        "run",
                        side_effect=failure,
                        return_value=subprocess.CompletedProcess([], 0),
                    ) as proc,
                    self.assertRaises((subprocess.TimeoutExpired, RuntimeError)),
                ):
                    agent.worker(root / "job.json")
                self.assertEqual(proc.call_count, 1)
                self.assertFalse(json.loads((root / "result.json").read_text())["ok"])


class DeliveryTests(unittest.TestCase):
    def test_receipt_validation_never_commits_pushes_or_creates_pr(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {
                "state_dir": tmp,
                "repo": "houlinchn/hl-pracitse",
                "owner": "houlinchn",
                "since": "2026-11-10",
            }
            gh = FakeGitHub()
            e = agent.Engine(cfg, gh)
            a = {"id": "job1", "worktree": tmp, "branch": "codex/10-issue-agent"}
            agent.atomic(Path(tmp) / "jobs/job1/job.json", {})
            pr = {
                "state": "open",
                "user": {"login": "houlinchn"},
                "head": {"ref": a["branch"], "sha": "sha1", "repo": {"full_name": cfg["repo"]}},
                "base": {"ref": "main", "repo": {"full_name": cfg["repo"]}},
                "changed_files": 2,
            }
            answer = {"pr_url": "https://github.com/houlinchn/hl-pracitse/pull/12"}
            with (
                patch.object(agent, "guard"),
                patch.object(gh, "api", return_value=pr) as api,
                patch.object(e, "git", side_effect=["sha1", ""]) as git,
            ):
                self.assertEqual(e.verify_delivery(a, answer), answer["pr_url"])
            api.assert_called_once_with("repos/houlinchn/hl-pracitse/pulls/12")
            self.assertEqual([c.args[1] for c in git.call_args_list], ["rev-parse", "status"])
            for change in (
                {"state": "closed"},
                {"user": {"login": "stranger"}},
                {"changed_files": 0},
                {"base": {"ref": "other", "repo": {"full_name": cfg["repo"]}}},
                {"head": {"ref": "other", "sha": "sha1", "repo": {"full_name": cfg["repo"]}}},
            ):
                with (
                    patch.object(agent, "guard"),
                    patch.object(gh, "api", return_value={**pr, **change}),
                    patch.object(e, "git", return_value="sha1"),
                    self.assertRaisesRegex(RuntimeError, "PR receipt"),
                ):
                    e.verify_delivery(a, answer)
            for url in ("https://github.com/stranger/repo/pull/12", "https://example.com/pr"):
                with self.assertRaisesRegex(RuntimeError, "configured repository"):
                    e.verify_delivery(a, {"pr_url": url})

    def test_real_git_scan_includes_untracked_staged_and_committed_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent.run(["git", "init", "--initial-branch=main", tmp])

            def git(*args):
                return agent.run(["git", "-C", tmp, *args])

            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            (root / "README.md").write_text("Initial\n")
            git("add", "README.md")
            git("commit", "-m", "Initial")
            base = git("rev-parse", "HEAD")
            (root / "safe.txt").write_text("Safe change\n")
            agent.check_files(tmp, base)
            (root / ".env").write_text("TEST_ONLY=placeholder\n")
            with self.assertRaisesRegex(RuntimeError, "credential file"):
                agent.check_files(tmp, base)
            (root / ".env").unlink()
            (root / "safe.txt").write_text("ghp_" + "x" * 36)
            with self.assertRaisesRegex(RuntimeError, "secret"):
                agent.check_files(tmp, base)
            git("add", "safe.txt")
            with self.assertRaisesRegex(RuntimeError, "secret"):
                agent.check_files(tmp, base)
            git("commit", "-m", "Synthetic credential test")
            with self.assertRaisesRegex(RuntimeError, "secret"):
                agent.check_files(tmp, base)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "issue_agent_install", Path(__file__).parents[1] / "scripts/issue_agent/install.py"
        )
        self.installer = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"agent": agent}):
            spec.loader.exec_module(self.installer)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = {
            "state_dir": str(self.root / "state"),
            "repo": "houlinchn/hl-pracitse",
            "owner": "houlinchn",
            "since": "2026-11-10",
            "excluded_issues": [4, 6],
        }
        self.config = self.root / "runtime/config.json"
        agent.atomic(self.config, self.cfg)
        self.target = self.config.with_name("agent.py")
        self.target.write_text("old_version = True\n")
        self.source = self.root / "new.py"
        self.source.write_text("new_version = True\n")
        self.state_file = Path(self.cfg["state_dir"]) / "state.json"
        agent.atomic(self.state_file, {"active": None, "issues": {"10": reviewed()}})

    def test_preview_is_read_only_and_never_touches_systemd(self):
        before = {p: p.read_bytes() for p in (self.target, self.config, self.state_file)}
        with patch.object(self.installer.subprocess, "run") as proc:
            preview = self.installer.upgrade(self.source, self.config, reconcile=10)
        proc.assert_not_called()
        self.assertFalse(preview["applied"])
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)

    def test_upgrade_backs_up_all_files_and_queues_discussion_without_approval(self):
        def systemctl(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, stdout="active\n")

        with patch.object(self.installer.subprocess, "run", side_effect=systemctl) as proc:
            result = self.installer.upgrade(
                self.source, self.config, apply=True, reconcile=10, exclude_issue=11
            )
        self.assertTrue(result["applied"])
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertEqual((Path(result["backup"]) / "agent.py").read_text(), "old_version = True\n")
        state = json.loads(self.state_file.read_text())
        self.assertEqual(state["issues"]["10"]["mode"], "plan_pending")
        self.assertNotIn("approval", state["issues"]["10"])
        self.assertIsNone(state["active"])
        self.assertEqual(json.loads(self.config.read_text())["excluded_issues"], [4, 6, 11])
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            proc.call_args.args[0], ["systemctl", "--user", "start", "hl-issue-agent.timer"]
        )

    def test_active_worker_or_paused_issue_prevents_changes(self):
        state = json.loads(self.state_file.read_text())
        state["active"] = {"id": "running"}
        agent.atomic(self.state_file, state)
        with (
            patch.object(self.installer.subprocess, "run") as proc,
            self.assertRaisesRegex(RuntimeError, "Active worker"),
        ):
            self.installer.upgrade(self.source, self.config, apply=True)
        proc.assert_not_called()
        state["active"] = None
        state["issues"]["10"]["mode"] = "paused"
        agent.atomic(self.state_file, state)
        with self.assertRaisesRegex(RuntimeError, "paused"):
            self.installer.upgrade(self.source, self.config, apply=True, reconcile=10)

    def test_failed_state_migration_restores_snapshot_and_timer(self):
        before = {p: p.read_bytes() for p in (self.target, self.config, self.state_file)}
        with (
            patch.object(
                self.installer.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout="active\n"),
            ) as proc,
            patch.object(self.installer, "Engine", side_effect=RuntimeError("migration failed")),
            self.assertRaisesRegex(RuntimeError, "migration failed"),
        ):
            self.installer.upgrade(self.source, self.config, apply=True, exclude_issue=11)
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)
        self.assertEqual(proc.call_args.args[0][-2:], ["start", "hl-issue-agent.timer"])

    def test_pause_arriving_during_upgrade_preparation_is_preserved(self):
        def systemctl(args, **kwargs):
            if "stop" in args:
                state = json.loads(self.state_file.read_text())
                state["issues"]["10"]["mode"] = "paused"
                agent.atomic(self.state_file, state)
            return subprocess.CompletedProcess(args, 0, stdout="active\n")

        with (
            patch.object(self.installer.subprocess, "run", side_effect=systemctl),
            self.assertRaisesRegex(RuntimeError, "paused"),
        ):
            self.installer.upgrade(self.source, self.config, apply=True, reconcile=10)
        self.assertEqual(json.loads(self.state_file.read_text())["issues"]["10"]["mode"], "paused")
        self.assertEqual(self.target.read_text(), "old_version = True\n")

    def test_inactive_timer_stays_inactive_and_invalid_numbers_are_rejected(self):
        with patch.object(
            self.installer.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 3, stdout="inactive\n"),
        ) as proc:
            self.installer.upgrade(self.source, self.config, apply=True)
        self.assertFalse(any("start" in c.args[0] for c in proc.call_args_list))
        for kwargs in (
            {"reconcile": 0},
            {"exclude_issue": -1},
            {"reconcile": 10, "exclude_issue": 10},
        ):
            with self.assertRaises(ValueError):
                self.installer.upgrade(self.source, self.config, **kwargs)


if __name__ == "__main__":
    unittest.main()
