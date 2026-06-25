import requests

r = requests.post(
    "http://127.0.0.1:11634/api/generate",
    json={
        "model": "qwen3.5:2b",
        "prompt": 'Reply ONLY with "OK". Do not think, just output: OK',
        "stream": False,
        "options": {"num_predict": 50},
    },
    timeout=120,
)
d = r.json()
print("response:", repr(d.get("response", "")[:200]))
print("thinking:", repr(d.get("thinking", "")[:300]))
print("status:", r.status_code)
