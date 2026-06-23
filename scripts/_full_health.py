import json
import subprocess
import sys
import time

sys.path.insert(0, r"D:\bobo\openclaw-foreign\workspace")

print("=== FULL SYSTEM HEALTH ===")
t0 = time.time()

# V7.0 compliance
from core.global_compliance import generate_soc2_report

soc2_path = generate_soc2_report()
soc2 = json.loads(soc2_path.read_text())
print(f" SOC2: {soc2['report_type']} chain_ok={soc2['chain_verified']} findings={len(soc2['findings'])}")

from core.international_billing import create_invoice

inv = create_invoice("TENANT_A", period_days=30)
print(f" Billing: {inv.get('status', 'N/A')} | {inv.get('currency', '?')} {inv.get('total', 'N/A')}")

from core.global_disaster_recovery import check_health as dr_health

dr = dr_health()
print(f" DR: regions={len(dr.get('regions', {}))} healthy={dr.get('healthy', 'N/A')}")

# V5.1 evolution
from core.evolution_engine import GIT_CMD, WHITELIST_PATCH_TARGETS

print(f" Evolution: whitelist={list(WHITELIST_PATCH_TARGETS)} git_ok={GIT_CMD is not None}")

# bus
from core.message_bus import bus as message_bus

message_bus.emit("system", "monitor", "health_check", {"status": "all_ok"})
print(" Bus: OK")

# CN hub
try:
    from cn_channels.publish_hub import PublishHub

    hub = PublishHub()
    print(" CN Hub: loaded OK")
except Exception as e:
    print(f" CN Hub: {e}")

# daemon re-check
r = subprocess.run(
    [sys.executable, r"D:\bobo\openclaw-foreign\skills\subconscious-daemon\run.py", "--json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
d = json.loads(r.stdout)
print(f" Daemon: {d['status']} | checks={len(d['checks'])} | alerts={d['alerts']}")

elapsed = time.time() - t0
print(f"\nALL SYSTEMS GO ({elapsed:.1f}s)")
