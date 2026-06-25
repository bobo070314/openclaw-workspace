"""Check the v1.1-self-evo-factory git remote"""

import subprocess

subdir = r"D:\bobo\openclaw-foreign\workspace\v1.1-self-evo-factory"

r = subprocess.run(
    f'git -C "{subdir}" remote -v', capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
)
print("v1.1-self-evo-factory remote:")
print(r.stdout if r.stdout.strip() else "(无 remote)")

r2 = subprocess.run(
    f'git -C "{subdir}" status --short', capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True
)
print("\n状态:")
print(r2.stdout if r2.stdout.strip() else "(clean)")

r3 = subprocess.run(
    f'git -C "{subdir}" branch --show-current',
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    shell=True,
)
print(f"分支: {r3.stdout.strip()}")
