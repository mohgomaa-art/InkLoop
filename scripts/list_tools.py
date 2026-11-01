import re

with open('backend/app/agent/registry.py', 'r', encoding='utf-8') as f:
    text = f.read()

tools = re.findall(r'tool_id="([^"]+)"', text)
names = re.findall(r'name="([^"]+)"', text)
for t, n in zip(tools, names):
    print(f"- {t}: {n}")
