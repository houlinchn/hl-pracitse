"""Authorization, cancellation, recovery and publication tests; no real API/model."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("agent", Path(__file__).parents[1] / "scripts/issue_agent/agent.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def issue(number=10, owner="houlinchn", created="2026-11-10T12:00:00Z"):
    return {"number": number, "title": "Improve UI", "body": "Explicit request", "state": "open",
            "created_at": created, "user": {"login": owner},
            "html_url": f"https://github.com/houlinchn/hl-pracitse/issues/{number}"}


def comment(body, cid=1, owner="houlinchn"):
    return {"body": body, "id": cid, "user": {"login": owner}, "created_at": "2026-11-10T12:10:00Z",
            "html_url": f"https://github.com/houlinchn/hl-pracitse/issues/10#issuecomment-{cid}"}


def reviewed():
    return {"mode": "human_review", "generation": 1, "seen": [], "digest": agent.digest(issue()),
            "plan": {"ready": True, "token": "a12345678901", "digest": agent.digest(issue()),
                     "main_sha": "main1", "dependencies": []}}


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
        cs = [comment("/codex ready a12345678901", 1, "stranger"), comment("/codex plan", 2),
              comment(agent.MARKER + "test -->", 3), comment("/codex plan", 4)]
        cfg = {"owner": "houlinchn"}
        self.assertEqual([c["id"] for c in agent.incoming(issue(), cs, s, cfg, "2026-11-10")], [4])
        self.assertEqual(agent.incoming(issue(owner="stranger"), cs, s, cfg, "2026-11-10"), [])

    def test_discussion_revokes_queued_approval(self):
        s = reviewed()
        agent.apply_comment(s, comment("/codex ready a12345678901"), issue())
        agent.apply_comment(s, comment("Also change permissions", 2), issue())
        self.assertEqual(s["mode"], "plan_pending")
        self.assertEqual(s["generation"], 2)

    def test_pause_resume_needs_fresh_plan(self):
        s = reviewed()
        agent.apply_comment(s, comment("/codex pause"), issue())
        agent.apply_comment(s, comment("casual discussion", 2), issue())
        self.assertEqual(s["mode"], "paused")
        agent.apply_comment(s, comment("/codex resume", 3), issue())
        self.assertEqual(s["mode"], "plan_pending")

    def test_public_reply_rejects_secret_before_post(self):
        gh = agent.GitHub({"owner": "houlinchn", "repo": "example/repo"})
        with patch.object(gh, "api") as api:
            with self.assertRaises(RuntimeError):
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
        self.cfg = {"state_dir": self.temp.name, "owner": "houlinchn", "since": "2026-11-10T00:00:00Z",
                    "excluded_issues": [4], "repo": "houlinchn/hl-pracitse"}
        self.gh = FakeGitHub()
        self.e = agent.Engine(self.cfg, self.gh)

    def test_historical_issue_and_tracker_never_autostart(self):
        self.gh.items = [issue(2, created="2026-11-08T00:00:00Z"), issue(4), issue(11, owner="stranger")]
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
        self.assertEqual(agent.incoming(issue(), self.gh.cs[10], restarted.state["issues"]["10"],
                                        self.cfg, self.cfg["since"]), [])

    def active(self, kind="develop"):
        a = {"id": "job1", "unit": "test-unit", "number": 10, "kind": kind, "generation": 1,
             "digest": agent.digest(issue()), "main_sha": "main1", "worktree": "/unused", "branch": "codex/10-issue-agent"}
        self.e.state.update(active=a, issues={"10": reviewed()})
        self.e.state["issues"]["10"]["mode"] = "developing" if kind == "develop" else "planning"
        self.gh.items = [issue()]
        return a

    def result(self, ready=True):
        agent.atomic(Path(self.temp.name) / "jobs/job1/result.json", {
            "ok": True, "answer": {"ready": ready, "message": "Verified", "risk": "L1", "dependencies": []}})

    @patch.object(agent.subprocess, "run")
    def test_pause_wins_over_finished_result(self, proc):
        self.active()
        self.result()
        self.gh.cs[10] = [comment("/codex pause")]
        with patch.object(self.e, "publish") as publish:
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
        with patch.object(self.e, "publish") as publish:
            self.e.poll()
        publish.assert_not_called()
        proc.assert_called_once()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "closed")

    def test_changed_body_wins_over_finished_result(self):
        self.active()
        self.result()
        self.gh.items[0]["body"] += " changed"
        with patch.object(agent.subprocess, "run"), patch.object(self.e, "publish") as publish, patch.object(self.e, "start") as start:
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(start.call_args.args[-1], "plan")

    def test_plan_does_not_publish_code(self):
        self.active("plan")
        self.result()
        with patch.object(self.e, "publish") as publish:
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "human_review")
        self.assertIn("/codex ready job1", self.gh.posts[(10, "result-job1")])

    def test_success_delivers_and_stops_in_review(self):
        self.active()
        self.result()
        with patch.object(self.e, "publish", return_value="https://example.com/pr") as publish:
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
        with patch.object(self.e, "publish") as publish:
            self.e.poll()
        publish.assert_not_called()
        self.assertEqual(self.e.state["issues"]["10"]["mode"], "blocked")

    def test_credentials_never_staged(self):
        for status in ("?? .env", " M secrets/private.key", "?? .local/staff-password"):
            with patch.object(self.e, "git", return_value=status) as git:
                with self.assertRaises(RuntimeError):
                    self.e.publish({"number": 10, "worktree": "/unused", "branch": "test"}, {"message": "done"})
                self.assertEqual(git.call_count, 1)

    def test_open_dependency_prevents_worker_launch(self):
        self.gh.items = [issue(10), issue(2)]
        s = reviewed()
        s["plan"]["dependencies"] = [2]
        self.cfg.update(repo_dir="/unused", base="main")
        with patch.object(self.e, "worktree", return_value=(Path("/unused"), "test")), patch.object(self.e, "git", return_value="main1"), patch.object(agent, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "Dependency #2"):
                self.e.start(issue(), s, "develop")
        run.assert_not_called()

    def test_changed_main_prevents_worker_launch(self):
        self.gh.items = [issue()]
        self.cfg.update(repo_dir="/unused", base="main")
        with patch.object(self.e, "worktree", return_value=(Path("/unused"), "test")), patch.object(self.e, "git", return_value="main2"), patch.object(agent, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "Base branch changed"):
                self.e.start(issue(), reviewed(), "develop")
        run.assert_not_called()


class LocalGitDeliveryTests(unittest.TestCase):
    def test_real_commit_push_and_pr_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote, work = root / "remote.git", root / "work"
            agent.run(["git", "init", "--bare", "--initial-branch=main", remote])
            agent.run(["git", "init", "--initial-branch=main", work])
            def git(*args):
                return agent.run(["git", "-C", work, *args])
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            (work / "README.md").write_text("Initial\n")
            git("add", "README.md")
            git("commit", "-m", "Initial")
            git("remote", "add", "origin", str(remote))
            git("push", "-u", "origin", "main")
            git("checkout", "-b", "codex/10-issue-agent")
            (work / "README.md").write_text("Approved change\n")
            cfg = {"state_dir": str(root / "state"), "owner": "houlinchn", "repo": "test/repo",
                   "gh": "fake-gh", "since": "2026-11-10", "git_email": "test@example.com"}
            gh = FakeGitHub([issue()])
            engine = agent.Engine(cfg, gh)
            original = agent.run
            created = []
            def cli(args, **kwargs):
                if str(args[0]) == "fake-gh":
                    return json.dumps([{"url": "https://example.com/pr"}] if created else [])
                return original(args, **kwargs)
            def api(endpoint, data):
                created.append(data)
                return {"html_url": "https://example.com/pr"}
            a = {"worktree": str(work), "branch": "codex/10-issue-agent", "number": 10}
            with patch.object(agent, "run", side_effect=cli), patch.object(gh, "api", side_effect=api):
                self.assertEqual(engine.publish(a, {"message": "Tests passed\nSecond line"}), "https://example.com/pr")
                head = git("rev-parse", "HEAD")
                self.assertEqual(engine.publish(a, {"message": "Tests passed"}), "https://example.com/pr")
                self.assertEqual(git("rev-parse", "HEAD"), head)
            self.assertEqual(len(created), 1)
            self.assertIn("Tests passed\nSecond line", created[0]["body"])
            self.assertEqual(git("status", "--porcelain"), "")
            self.assertEqual(agent.run(["git", "--git-dir", remote, "rev-parse", "refs/heads/codex/10-issue-agent"]), head)


if __name__ == "__main__":
    unittest.main()
