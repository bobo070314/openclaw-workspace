import os
import time

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False

# Test: simple text task qwen can handle
prompt = "用中文写一个简短的软件需求描述，50字以内，关于一个在线计数器工具："

t0 = time.time()
r = s.post(
    "http://127.0.0.1:11634/api/generate",
    json={
        "model": "qwen3.5:2b",
        "prompt": prompt,
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": 256, "num_predict": 100, "temperature": 0.1},
    },
    timeout=30,
)
elapsed = time.time() - t0
print(f"Elapsed: {elapsed:.1f}s")
d = r.json()
resp = d.get("response", "") or d.get("thinking", "")
print(f"Result: {resp}")
