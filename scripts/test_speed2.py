import os
import time

import requests

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
s = requests.Session()
s.trust_env = False

# Test: the simplest possible generate to verify Ollama is responsive
tests = [
    ("hello", "Say 'hello'", 30),
    ("code_short", "output:\n[OUTPUT]\nfunction hello() { console.log(1); }\n[/OUTPUT]", 60),
]

for name, prompt, timeout in tests:
    t0 = time.time()
    try:
        r = s.post(
            "http://127.0.0.1:11634/api/generate",
            json={
                "model": "qwen3.5:2b",
                "prompt": prompt,
                "stream": False,
                "keep_alive": -1,
                "options": {"num_ctx": 256, "num_predict": 64, "temperature": 0.1},
            },
            timeout=timeout,
        )
        elapsed = time.time() - t0
        d = r.json()
        print(f"[{name}] {elapsed:.1f}s | resp={d.get('response', '')[:100]}")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{name}] {elapsed:.1f}s | ERROR: {e}")
