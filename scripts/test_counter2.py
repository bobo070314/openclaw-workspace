import os
import time

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False

# Strategy: put code FIRST in prompt, ask qwen to just complete it
prompt = """import React, { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div className="flex flex-col items-center gap-6 p-8">
      <h2 className="text-2xl font-bold">计数器</h2>
"""
# Let qwen auto-complete the rest

t0 = time.time()
r = s.post(
    "http://127.0.0.1:11634/api/generate",
    json={
        "model": "qwen3.5:2b",
        "prompt": prompt,
        "stream": False,
        "keep_alive": -1,
        "options": {"num_ctx": 512, "num_predict": 200, "temperature": 0.1, "stop": ["```", "\n\n\n"]},
    },
    timeout=60,
)
elapsed = time.time() - t0
print(f"Elapsed: {elapsed:.1f}s")
d = r.json()
resp = d.get("response", "")
thinking = d.get("thinking", "")
full_output = resp or thinking
print(f"Output({len(full_output)}):")
print("---")
print(full_output)
print("---")
