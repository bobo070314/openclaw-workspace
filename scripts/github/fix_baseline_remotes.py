import subprocess
from pathlib import Path

UPSTREAM = {
    "cursor": "https://github.com/getcursor/cursor.git",
    "dify": "https://github.com/langgenius/dify.git",
    "eve": "https://github.com/StanzaLab/eve.git",
    "lobe-chat": "https://github.com/lobehub/lobe-chat.git",
    "n8n": "https://github.com/n8n-io/n8n.git",
    "prisma": "https://github.com/prisma/prisma.git",
    "stripe": "https://github.com/stripe/stripe-node.git",
    "supabase": "https://github.com/supabase/supabase.git",
    "temporal": "https://github.com/temporalio/temporal.git",
    "trpc": "https://github.com/trpc/trpc.git",
}

base = Path(r"D:\bobo\openclaw-foreign\workspace\gh-enterprise-baseline")
for name, remote_url in UPSTREAM.items():
    p = base / name / ".git"
    if not p.exists():
        print(f"  ? {name} — NOT a git repo")
        continue
    repo_dir = str(base / name)
    r = subprocess.run(["git", "-C", repo_dir, "remote", "-v"], capture_output=True, text=True, encoding="utf-8")
    if r.stdout.strip():
        lines = [l for l in r.stdout.strip().split("\n") if l.startswith("origin")]
        if lines:
            cur = lines[0].split("\t")[1].split(" ")[0] if "\t" in lines[0] else "?"
            print(f"  = {name}: origin already set -> {cur[:60]}")
        else:
            subprocess.run(["git", "-C", repo_dir, "remote", "add", "origin", remote_url])
            print(f"  + {name}: origin added")
    else:
        subprocess.run(["git", "-C", repo_dir, "remote", "add", "origin", remote_url])
        print(f"  + {name}: origin added")
print("\nDone")
