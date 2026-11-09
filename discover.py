import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SOURCE = "https://www.noon.com/saudi-en/noon-deals-sa/"
OUTPUT = Path("candidates.json")


class ProductLinks(HTMLParser):
    def _init_(self):
        super()._init_()
        self.links = {}

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        data = dict(attrs)
        href = data.get("href", "")
        url = urljoin(SOURCE, href)
        parsed = urlparse(url)

        if parsed.hostname not in ("noon.com", "www.noon.com"):
            return

        # Noon product URLs commonly contain /p/ or /N...
        if not re.search(r"/p/|/N[A-Z0-9]{8,}", parsed.path, re.I):
            return

        clean_url = parsed._replace(
            query="", fragment=""
        ).geturl()

        self.links[clean_url] = {
            "merchant": "Noon",
            "official_url": clean_url,
            "source_page": SOURCE,
            "status": "candidate_unverified"
        }


def main():
    request = urllib.request.Request(
        SOURCE,
        headers={
            "User-Agent": "SaudiDealsHunter/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request, timeout=30
        ) as response:
            html = response.read().decode(
                "utf-8", errors="replace"
            )
    except Exception as exc:
        print(f"Noon source unavailable: {exc}")
        print("Skipping Noon. No verified offers found.")

        OUTPUT.write_text(
            "[]\n",
            encoding="utf-8"
        )
        return

    parser = ProductLinks()
    parser.feed(html)

    candidates = list(parser.links.values())

    for item in candidates:
        item["discovered_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

    OUTPUT.write_text(
        json.dumps(
            candidates,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print(f"Collected {len(candidates)} Noon candidates")
    print("Candidates are NOT verified deals.")

    if not candidates:
        print(
            "No product links found. The page may "
            "use JavaScript rendering or a changed "
            "HTML structure."
        )


if __name__ == "__main__":
    main()
