import json
import os
import urllib.request
from pathlib import Path

OUTPUT = Path("candidates.json")

def discover():
    urls = [
        url.strip()
        for url in os.getenv("DEAL_FEED_URLS", "").split(",")
        if url.strip()
    ]

    candidates = []

    for url in urls:
        if not url.startswith("https://"):
            print("Skipping non-HTTPS feed")
            continue

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SaudiDealsHunter/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                data = json.load(response)

            if not isinstance(data, list):
                print("Skipping invalid feed format")
                continue

            for item in data:
                if isinstance(item, dict):
                    candidates.append(item)

        except Exception as exc:
            print("Feed error:", type(exc)._name_)

    OUTPUT.write_text(
        json.dumps(candidates, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Collected {len(candidates)} candidates")
    print("Candidates are NOT verified deals.")

if __name__ == "__main__":
    discover()
