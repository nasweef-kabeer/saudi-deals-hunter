
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
STATE = Path("seen.json")

QUERIES = [
    'Saudi Arabia ("free gift" OR "free sample" OR "gift card giveaway") (Amazon OR noon OR SHEIN OR Temu)',
    'Saudi Arabia ("flash sale" OR "limited time offer") (noon OR Amazon OR Trendyol)',
    'السعودية ("هدية مجانية" OR "بطاقة هدية" OR "عروض فلاش")',
]

GOOD = re.compile(
    r"free gift|free sample|gift card|giveaway|flash sale|limited.time|هدية مجانية|بطاقة هدية|عروض فلاش",
    re.I,
)
BAD = re.compile(
    r"generator|hack|crack|unlimited free|survey reward|gift card code generator",
    re.I,
)


def send(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    body = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST")

    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError("Telegram rejected message")


def fetch(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query,
        "hl": "en",
        "gl": "SA",
        "ceid": "SA:en",
    })

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SaudiDealsHunter/1.0"},
    )

    with urllib.request.urlopen(req, timeout=25) as response:
        root = ET.fromstring(response.read())

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()

        if title and link and GOOD.search(title) and not BAD.search(title):
            yield title, link


def main():
    test_mode = (
        "--test" in sys.argv
        or os.getenv("TEST_MESSAGE", "").lower() == "true"
    )

    if test_mode:
        send(
            "✅ Saudi Deals Hunter test successful!\n\n"
            "Your GitHub Actions bot can send Telegram messages.\n"
            "This is a test, not a shopping offer."
        )
        print("Telegram test sent successfully.")
        return

    first_run = not STATE.exists()

    seen = set()
    if not first_run:
        seen = set(json.loads(STATE.read_text()))

    found = []
    errors = []

    for query in QUERIES:
        try:
            found.extend(fetch(query))
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    if errors:
        print("Feed errors:", *errors, sep="\n")

    if not found and errors:
        raise RuntimeError("No feeds could be checked successfully")

    new = []
    for title, link in found:
        key = title.casefold()
        if key not in seen:
            new.append((title, link, key))
            seen.add(key)

    if first_run:
        STATE.write_text(
            json.dumps(sorted(seen), ensure_ascii=False, indent=2)
            + "\n"
        )
        print(
            f"Initialized baseline with {len(seen)} headlines. "
            "No alerts on first run."
        )
        return

    # News headlines are not independently verified offers.
    # Keep them for review instead of automatically sending
    # unverified promotions as deal alerts.
    STATE.write_text(
        json.dumps(sorted(seen)[-1500:], ensure_ascii=False, indent=2)
        + "\n"
    )

    print(
        f"Checked {len(found)} matching headlines; "
        f"found {len(new)} new leads. "
        "No unverified deal alerts sent."
    )


if __name__ == "__main__":
    main()
