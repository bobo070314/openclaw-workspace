import json
import os
from pathlib import Path

# ========== 1) openclaw.json entries 未启用但质量达标的 extraDirs 技能 ==========
sk_dir = r"D:\bobo\openclaw-foreign\skills"
with open(r"D:\bobo\openclaw-foreign\openclaw.json", "r", encoding="utf-8-sig") as f:
    d = json.load(f)
ents = d["skills"]["entries"]
extra = set(os.listdir(sk_dir))
missing = sorted(extra - set(ents.keys()))
missing = [n for n in missing if not n.startswith("_") and not n.startswith(".") and not n.endswith(".py")]

print("=" * 70)
print("一号缺失：ExtraDirs 技能未启用（31个）")
print("=" * 70)
# 按质量分类
v2ready = []
stubs = []
for n in missing:
    rp = Path(sk_dir) / n / "run.py"
    if rp.exists():
        content = rp.read_text(encoding="utf-8", errors="replace")
        has_v2 = "--version" in content and "--json" in content and "--dry-run" in content
    else:
        has_v2 = False
    if has_v2:
        v2ready.append(n)
    else:
        stubs.append(f"{n} ({rp.stat().st_size if rp.exists() else 0}b, --ver/--json/--dry-run incomplete)")

print(f"\nv0.2.0 达标(可一键启用): {len(v2ready)}")
for n in v2ready:
    print(f"  + {n}")
print(f"\n需修复/淘汰: {len(stubs)}")
for s in stubs:
    print(f"  ? {s}")

# ========== 2) v1.1-self-evo-factory core 模块未纳入 pipeline ==========
print("\n" + "=" * 70)
print("二号缺失：core/ 模块未纳入 orchestrator pipeline")
print("=" * 70)
core_dir = Path(r"D:\bobo\projects\v1.1-self-evo-factory\core")
orc_path = core_dir / "core_orchestrator.py"
if orc_path.exists():
    oc = orc_path.read_text(encoding="utf-8", errors="replace")
    core_files = set(f.stem for f in core_dir.glob("*.py"))
    oc_refs = set()
    for f in core_files:
        if f"_{f}" in oc or f"from core.{f}" in oc or f"import {f}" in oc:
            oc_refs.add(f)
    unref = core_files - oc_refs - {"__init__"}
    print(f"core/ modules: {len(core_files)}, referenced in orchestrator: {len(oc_refs)}")
    for u in sorted(unref):
        print(f"  ? {u}.py — not referenced")

# ========== 3) gh-enterprise-baseline ==========
print("\n" + "=" * 70)
print("三号缺失：gh-enterprise-baseline 子仓库状态")
print("=" * 70)
ghe = Path(r"D:\bobo\openclaw-foreign\workspace\gh-enterprise-baseline")
repos = [d for d in ghe.iterdir() if d.is_dir() and (d / ".git").exists()]
for r in repos:
    # 检查是否有远程
    try:
        remotes = __import__("subprocess").run(["git", "-C", str(r), "remote", "-v"], capture_output=True, text=True)
        has_remote = bool(remotes.stdout.strip())
    except:
        has_remote = False
    # 检查最近提交
    try:
        last = __import__("subprocess").run(
            ["git", "-C", str(r), "log", "--oneline", "-1"], capture_output=True, text=True
        )
        last_commit = last.stdout.strip()[:60]
    except:
        last_commit = "ERR"
    print(f"  {r.name:25s} remote={str(has_remote):5s} last={last_commit}")

# ========== 4) workspace 脏文件 ==========
print("\n" + "=" * 70)
print("四号缺失：workspace 根目录残留")
print("=" * 70)
ws = Path(r"D:\bobo\openclaw-foreign\workspace")
for f in ws.iterdir():
    if f.is_file() and not f.name.startswith(".") and f.suffix not in (".md", ".json", ".toml", ".gitignore"):
        print(f"  ? {f.name} ({f.stat().st_size}b)")

# ========== 5) 系统环境变量非持久化 ==========
print("\n" + "=" * 70)
print("五号缺失：环境变量非持久化")
print("=" * 70)
import os as os2

for var in ["DEEPSEEK_API_KEY", "OLLAMA_HOST", "PYTHONIOENCODING", "HTTP_PROXY", "HTTPS_PROXY"]:
    val = os2.environ.get(var, "")
    if val:
        print(f"  ✓ {var}=...{val[-8:] if len(val) > 20 else val}")
    else:
        print(f"  ✗ {var}=MISSING")
