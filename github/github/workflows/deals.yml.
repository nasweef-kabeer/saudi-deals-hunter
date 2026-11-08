import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
STATE = Path('seen.json')
QUERIES = [
    'Saudi Arabia ("free gift" OR "free sample" OR "gift card giveaway") (Amazon OR noon OR SHEIN OR Temu)',
    'Saudi Arabia ("flash sale" OR "limited time offer") (noon OR Amazon OR Trendyol)',
    'السعودية ("هدية مجانية" OR "بطاقة هدية" OR "عروض فلاش")',
]
GOOD = re.compile(r'free gift|free sample|gift card|giveaway|flash sale|limited.time|هدية مجانية|بطاقة هدية|عروض فلاش', re.I)
BAD = re.compile(r'generator|hack|crack|unlimited free|survey reward|gift card code generator', re.I)


def send(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    body = urllib.parse.urlencode({'chat_id': CHAT_ID, 'text': message, 'disable_web_page_preview': 'true'}).encode()
    req = urllib.request.Request(url, data=body, method='POST')
    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Telegram rejected message')


def fetch(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl': 'en', 'gl': 'SA', 'ceid': 'SA:en'})
    req = urllib.request.Request(url, headers={'User-Agent': 'SaudiDealsHunter/1.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        root = ET.fromstring(response.read())
    for item in root.findall('./channel/item'):
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        if title and link and GOOD.search(title) and not BAD.search(title):
            yield title, link


def main():
    if '--test' in sys.argv:
        send('✅ Saudi Deals Hunter test successful! Your GitHub Actions bot can send Telegram messages. This is a test, not a shopping offer.')
        print('Telegram test sent.')
        return
    seen = set(json.loads(STATE.read_text()) if STATE.exists() else [])
    found = []
    errors = []
    for query in QUERIES:
        try:
            found.extend(fetch(query))
        except Exception as exc:
            errors.append(type(exc).__name__ + ': ' + str(exc))
    if errors:
        print('Feed errors:', *errors, sep='\n')
    if not found and errors:
        raise RuntimeError('No feeds could be checked successfully')
    new = []
    for title, link in found:
        key = title.casefold()
        if key not in seen:
            new.append((title, link, key))
            seen.add(key)
    # First run initializes the baseline without flooding the chat with old deals.
    if not STATE.exists():
        STATE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2) + '\n')
        print(f'Initialized baseline with {len(seen)} headlines. No alerts on first run.')
        return
    for title, link, _ in new[:5]:
        send('🎁 POSSIBLE SAUDI DEAL (NOT VERIFIED)\n' + title[:250] + '\n' + link + '\n\nCheck merchant website, expiry, eligibility, shipping and final price before claiming.')
    # Keep remaining new items for future checking, avoiding duplicate alerts.
    sent = {key for _, _, key in new[:5]}
    old = set(json.loads(STATE.read_text()))
    STATE.write_text(json.dumps(sorted(old | sent)[-1500:], ensure_ascii=False, indent=2) + '\n')
    print(f'Sent {min(5, len(new))} new leads.')


if __name__ == '__main__':
    main()
