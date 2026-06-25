import os
import time

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False

t0 = time.time()
r = s.post(
    "http://127.0.0.1:11634/api/generate",
    json={
        "model": "qwen3.5:2b",
        "prompt": "Write a React counter component with useState. Output ONLY the code inside [OUTPUT][/OUTPUT] tags. Do not explain.\n\n[OUTPUT]\n",
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": 512, "num_predict": 256, "temperature": 0.1},
    },
    timeout=120,
)
elapsed = time.time() - t0
print(f"Elapsed: {elapsed:.1f}s")
d = r.json()
resp = d.get("response", "")
thinking = d.get("thinking", "")
print(f"Response({len(resp)}): {resp[:400]}")
print(f"Thinking({len(thinking)}): {thinking[-300:] if thinking else 'NONE'}")
