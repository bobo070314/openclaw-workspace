import os

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False
r = s.post(
    "http://127.0.0.1:11634/api/generate",
    json={"model": "qwen3.5:2b", "prompt": "你好", "stream": False, "keep_alive": -1},
    timeout=300,
)
print(f"Status: {r.status_code}")
data = r.json()
resp = data.get("response", "")
thinking = data.get("thinking", "")
print(f"Response({len(resp)}): {resp[:200]}")
print(f"Thinking({len(thinking)}): {thinking[-300:]}")
