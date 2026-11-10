#!/usr/bin/env python3
"""Preview or apply an explicitly approved upgrade of the existing issue service."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from agent import Engine, atomic, now


def validate_state(state, cfg, reconcile):
    if state.get("active"):
        raise RuntimeError("Active worker exists; wait or pause it before upgrading")
    if reconcile is not None:
        s = state["issues"].get(str(reconcile))
        if (
            not s
            or s["mode"] in ("ignored", "paused", "closed")
            or reconcile in cfg.get("excluded_issues", [])
        ):
            raise RuntimeError("Selected issue is absent, excluded, paused or closed")


def upgrade(source, config, apply=False, reconcile=None, exclude_issue=None):
    if any(n is not None and n <= 0 for n in (reconcile, exclude_issue)) or (
        reconcile is not None and reconcile == exclude_issue
    ):
        raise ValueError("Issue numbers must be positive and reconcile cannot be excluded")
    source, config = Path(source).resolve(), Path(config).resolve()
    content = source.read_bytes()
    compile(content, str(source), "exec")
    cfg = json.loads(config.read_text())
    target = config.parent / "agent.py"
    state_file = Path(cfg["state_dir"]) / "state.json"
    state = json.loads(state_file.read_text())
    validate_state(state, cfg, reconcile)
    preview = {
        "source": str(source),
        "target": str(target),
        "sha256": hashlib.sha256(content).hexdigest(),
        "reconcile": reconcile,
        "exclude_issue": exclude_issue,
        "applied": False,
    }
    if not apply:
        return preview
    active = subprocess.run(
        ["systemctl", "--user", "is-active", "hl-issue-agent.timer"],
        capture_output=True,
        text=True,
        check=False,
    )
    if active.returncode not in (0, 3):
        raise RuntimeError("Cannot determine timer state; upgrade cancelled")
    timer_running = active.stdout.strip() == "active"
    backup = (
        Path(cfg["state_dir"]) / "backups" / ("upgrade-" + now().replace(":", "").replace(".", ""))
    )
    saved = False
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", "hl-issue-agent.timer", "hl-issue-agent.service"],
            check=True,
        )
        with (Path(cfg["state_dir"]) / "poll.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state = json.loads(state_file.read_text())
            cfg = json.loads(config.read_text())
            validate_state(state, cfg, reconcile)
            backup.mkdir(parents=True, mode=0o700)
            for file in (target, config, state_file):
                shutil.copy2(file, backup / file.name)
                (backup / file.name).chmod(0o600)
            saved = True
            if exclude_issue is not None:
                cfg["excluded_issues"] = sorted(
                    set(cfg.get("excluded_issues", []) + [exclude_issue])
                )
                atomic(config, cfg)
            engine = Engine(cfg)
            if reconcile is not None:
                s = engine.state["issues"][str(reconcile)]
                s.update(
                    discussion_from=s["mode"], mode="plan_pending", generation=s["generation"] + 1
                )
            engine.save()
            temp = target.with_suffix(".new")
            temp.write_bytes(content)
            temp.chmod(0o600)
            temp.replace(target)
            preview.update(applied=True, backup=str(backup))
            atomic(backup / "installation.json", preview)
    except Exception:
        # The timer is stopped and no worker was launched, so restoring this
        # snapshot cannot replay external operations performed by the new code.
        if saved:
            for file in (target, config, state_file):
                temp = file.with_suffix(file.suffix + ".restore")
                shutil.copy2(backup / file.name, temp)
                temp.replace(file)
        raise
    finally:
        if timer_running:
            subprocess.run(["systemctl", "--user", "start", "hl-issue-agent.timer"], check=True)
    return preview


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="/home/muise/.local/share/hl-pracitse-issue-agent/config.json"
    )
    parser.add_argument("--source", default=str(Path(__file__).with_name("agent.py")))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply an explicitly approved upgrade; default is preview only",
    )
    parser.add_argument(
        "--reconcile",
        type=int,
        help="Queue one existing issue for discussion, never fabricate a Ready comment",
    )
    parser.add_argument(
        "--exclude-issue",
        type=int,
        help="Exclude the manually handled upgrade issue from the listener",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            upgrade(args.source, args.config, args.apply, args.reconcile, args.exclude_issue),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
