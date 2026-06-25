import os
import time

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False

# Test [OUTPUT] extraction with the real prompt
prompt = "你是全栈开发工程师。输出React代码。要求：输出放在 [OUTPUT] 和 [/OUTPUT] 之间，不要解释。\n\n用户请求：帮我写一个React计数器组件\n\n[OUTPUT]\n"

t0 = time.time()
r = s.post(
    "http://127.0.0.1:11634/api/generate",
    json={
        "model": "qwen3.5:2b",
        "prompt": prompt,
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": 512, "num_predict": 256, "temperature": 0.1},
    },
    timeout=90,
)
elapsed = time.time() - t0
print(f"Elapsed: {elapsed:.1f}s")
d = r.json()
resp = d.get("response", "")
thinking = d.get("thinking", "")
print(f"Response({len(resp)}): [{resp[:200]}]")
print(f"Thinking({len(thinking)}) last 400: [{thinking[-400:]}]")
