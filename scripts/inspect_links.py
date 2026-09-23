import re
from pathlib import Path

files = [
    Path(r"C:\Users\rajva\.gemini\antigravity\brain\ab1e4628-b606-487e-9563-a00343b66342\.system_generated\steps\400\content.md"),
    Path(r"C:\Users\rajva\.gemini\antigravity\brain\ab1e4628-b606-487e-9563-a00343b66342\.system_generated\steps\402\content.md")
]

for fp in files:
    if fp.exists():
        print(f"--- Checking {fp.name} ---")
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if any(k in line.lower() for k in ["linkedin", "github.com", "portfolio", "hrishith"]):
                if len(line.strip()) < 300:
                    print("Match:", line.strip())
