"""Kairos GitHub repository monitor - checks repository activity via gh CLI."""

import subprocess


def gh_query(endpoint, jq_filter, limit=5):
    """Run a gh api query with jq output."""
    cmd = ["gh", "api", endpoint, "-q", jq_filter]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        stderr = r.stderr.strip() if r.stderr else ""
        return f"ERR ({r.returncode}): {stderr}"
    return r.stdout.strip() if r.stdout else ""


def get_commits(repo, count=5):
    """Get recent commits for a repo."""
    jq = f'.[0:{count}][]|[(.commit.committer.date)[0:10],.sha[0:7],(.commit.message|split("\\n")[0])]|@tsv'
    return gh_query(f"repos/{repo}/commits", jq)


def get_releases(repo, count=3):
    """Get recent releases for a repo."""
    jq = f".[0:{count}][]|[.tag_name,.name,.published_at]|@tsv"
    return gh_query(f"repos/{repo}/releases", jq)


def get_pulls(repo, count=5):
    """Get recent pull requests for a repo."""
    jq = f".[0:{count}][]|[.number,.state,.title,.user.login]|@tsv"
    return gh_query(f"repos/{repo}/pulls?state=all&sort=updated&direction=desc", jq)


def get_open_issues(repo, count=5):
    """Get open issues for a repo."""
    jq = f".[0:{count}][]|[.number,.state,.title,.user.login]|@tsv"
    return gh_query(f"repos/{repo}/issues?state=open", jq)


def get_notifications(count=10):
    """Get recent GitHub notifications."""
    jq = f".[0:{count}][]|[.updated_at,.subject.title,.subject.type,.repository.full_name,.reason]|@tsv"
    return gh_query("notifications", jq)


def main():
    repos = [
        "bobo070314/v1.1-self-evo-factory",
        "bobo070314/openclaw-foreign-workspace",
        "bobo070314/docs",
    ]

    print("=" * 70)
    print("KAIROS: GitHub Repository Monitor")
    print("=" * 70)

    for repo in repos:
        print(f"\n--- {repo} ---")
        commits = get_commits(repo)
        print(f"  Recent commits:\n    {commits.replace(chr(9), '  ')}" if commits else "  (none)")

    # Primary repo: more details
    primary = "bobo070314/v1.1-self-evo-factory"
    print(f"\n--- {primary} - Releases ---")
    releases = get_releases(primary)
    print(f"  {releases.replace(chr(9), '  ')}" if releases else "  (none)")

    print(f"\n--- {primary} - Pull Requests ---")
    pulls = get_pulls(primary)
    print(f"  {pulls.replace(chr(9), '  ')}" if pulls else "  (none)")

    print(f"\n--- {primary} - Open Issues ---")
    issues = get_open_issues(primary)
    print(f"  {issues.replace(chr(9), '  ')}" if issues else "  (none)")

    print("\n--- Notifications (recent 10) ---")
    notifs = get_notifications()
    print(f"  {notifs.replace(chr(9), '  ')}" if notifs else "  (none)")

    print("\n" + "=" * 70)
    print("Monitor complete.")


if __name__ == "__main__":
    main()
