"""Kairos GitHub monitor — gh CLI wrapper with proper encoding handling."""

import json
import os
import subprocess
import sys


def gh(*args):
    """Run gh CLI with proper encoding."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(
        ["gh"] + list(args),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if r.returncode != 0:
        print(f"[ERR] gh {' '.join(args)}: {r.stderr.strip()}", file=sys.stderr)
        return None
    return r.stdout.strip()


def main():
    print("=== Kairos GitHub Monitor ===")
    print("Time: 2026-06-25 17:26 CST")

    # 1. Auth check
    auth = gh("auth", "status")
    if auth is None:
        print("[FATAL] gh auth failed")
        return 1
    print("Auth: OK (bobo070314)")

    # 2. Main repo info
    print("\n--- Main repo: bobo070314/v1.1-self-evo-factory ---")
    repo_json = gh(
        "repo",
        "view",
        "bobo070314/v1.1-self-evo-factory",
        "--json",
        "name,updatedAt,pushedAt,defaultBranchRef,description",
    )
    if repo_json:
        repo = json.loads(repo_json)
        print(f"  Name:    {repo['name']}")
        print(f"  Desc:    {repo.get('description', '')}")
        print(f"  Updated: {repo['updatedAt']}")
        print(f"  Pushed:  {repo['pushedAt']}")
        print(f"  Branch:  {repo['defaultBranchRef']['name']}")

    # 3. Recent events
    print("\n--- Recent events (last 10) ---")
    events_raw = gh("api", "/users/bobo070314/events?per_page=10")
    if events_raw:
        events = json.loads(events_raw)
        for e in events[:10]:
            etype = e["type"]
            repo_name = e["repo"]["name"]
            created = e["created_at"]
            payload = e.get("payload", {})
            detail = payload.get("action", "") or payload.get("ref", "") or ""
            commits = payload.get("commits", [])
            if commits:
                msgs = ", ".join(c["message"].split("\n")[0][:60] for c in commits[:3])
                detail = f"{len(commits)} commits: {msgs}"
            print(f"  {etype:30s} | {repo_name:35s} | {created} | {detail}")
    else:
        print("  (failed to fetch)")

    # 4. Notifications
    print("\n--- Notifications (unread, last 5) ---")
    notifs_raw = gh("api", "/notifications?per_page=5")
    if notifs_raw:
        notifs = json.loads(notifs_raw)
        if not notifs:
            print("  (none)")
        for n in notifs[:5]:
            subj = n.get("subject", {})
            print(f"  {n['reason']:15s} | {n['repository']['full_name']:35s} | {subj.get('title', '')[:80]}")
        print(f"  Total shown: {len(notifs)}")
    else:
        print("  (failed to fetch)")

    # 5. List all repos
    print("\n--- My repos (recently updated, top 5) ---")
    repos_raw = gh("api", "/users/bobo070314/repos?per_page=30&sort=updated&direction=desc")
    if repos_raw:
        repos = json.loads(repos_raw)
        for r in repos[:5]:
            print(
                f"  {r['name']:40s} | updated: {r['updated_at']} | pushed: {r['pushed_at']} | lang: {r.get('language', 'N/A') or 'N/A'}"
            )

    print("\n[DONE]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
