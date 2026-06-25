import os
import sys

sys.path.insert(0, r"D:\bobo\projects\v1.1-self-evo-factory")

for k in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)

from core.local_llm import INFERENCE_TIMEOUT, chat, is_ollama_alive

print(f"Ollama alive: {is_ollama_alive()}, timeout={INFERENCE_TIMEOUT}")

# Super minimal prompt
prompt = "[OUTPUT]\nimport React, { useState } from 'react';\nexport default function Counter() {\n  const [count, setCount] = useState(0);\n  return <div>Count: {count}</div>;\n}\n[/OUTPUT]"

# Actually ask something useful but short
prompt = "输出一个React计数器组件，用[OUTPUT]标签包裹：\n\n[OUTPUT]\n"

print(f"Prompt: {len(prompt)} chars")
result, source = chat(prompt)
print(f"\nSource: {source}")
print(f"Result ({len(result)} chars):")
print("---BEGIN---")
print(result[:500])
print("---END---")
