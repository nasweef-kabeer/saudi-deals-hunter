import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE = Path('seen.json')
OFFERS = Path('offers.json')


def send(message):
    token = os.environ['TELEGRAM_BOT_TOKEN'].strip()
    chat_id = os.environ['TELEGRAM_CHAT_ID'].strip()
    if not token or not chat_id:
        raise ValueError('Telegram secrets must not be empty')
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = urllib.parse.urlencode({'chat_id': chat_id, 'text': message, 'disable_web_page_preview': 'true'}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=payload, method='POST'), timeout=25) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Telegram HTTP {error.code}. Check bot token, chat ID and bot permissions.') from None
    if not result.get('ok'):
        raise RuntimeError('Telegram rejected message')


def verified(offer):
    required = ('title', 'merchant', 'official_url', 'saudi_eligible', 'price_sar', 'shipping_sar', 'expires_at', 'requirements', 'verified_at', 'source_type')
    if not isinstance(offer, dict) or any(k not in offer for k in required):
        return False, 'missing required information'
    try:
        parsed = urllib.parse.urlparse(offer['official_url'])
        if parsed.scheme != 'https' or not parsed.hostname:
            return False, 'invalid official link'
        domains = ('amazon.sa', 'noon.com', 'temu.com', 'aliexpress.com', 'shein.com', 'trendyol.com')
        host = parsed.hostname.lower()
        if not any(host == domain or host.endswith('.' + domain) for domain in domains):
            return False, 'merchant domain not allowlisted'
        if offer['saudi_eligible'] is not True or offer['source_type'] != 'official_merchant':
            return False, 'not independently confirmed as Saudi-eligible official merchant offer'
        price, shipping = float(offer['price_sar']), float(offer['shipping_sar'])
        if price < 0 or shipping < 0:
            return False, 'negative price or shipping'
        expiry = datetime.fromisoformat(offer['expires_at'].replace('Z', '+00:00'))
        checked = datetime.fromisoformat(offer['verified_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        if expiry.tzinfo is None or checked.tzinfo is None or expiry <= now or checked > now or (now - checked).total_seconds() > 86400:
            return False, 'expired, stale or invalid verification timestamp'
        if not str(offer['title']).strip() or not str(offer['requirements']).strip():
            return False, 'missing description or requirements'
        if not offer.get('independently_checked', False):
            return False, 'merchant checkout and terms not independently checked'
        if not offer.get('qualifies', False):
            return False, 'not marked worthwhile after comparison'
        return True, ''
    except (ValueError, TypeError, KeyError, OverflowError):
        return False, 'invalid price, date or field type'


def main():
    if '--test' in sys.argv or os.getenv('TEST_MESSAGE', '').lower() == 'true':
        send('✅ Saudi Deals Hunter Telegram test successful. This is not a shopping offer.')
        print('Telegram test sent.')
        return
    if not OFFERS.exists():
        print('No offers.json supplied. No verified offers to alert. GitHub job succeeded; discovery is not configured.')
        return
    offers = json.loads(OFFERS.read_text(encoding='utf-8'))
    if not isinstance(offers, list):
        raise ValueError('offers.json must contain a JSON array')
    seen = set(json.loads(STATE.read_text(encoding='utf-8'))) if STATE.exists() else set()
    approved = 0
    rejected = 0
    for offer in offers:
        ok, reason = verified(offer)
        if not ok:
            rejected += 1
            print('Rejected offer:', reason)
            continue
        identity = f"{offer['official_url']}|{offer['price_sar']}|{offer['expires_at']}"
        key = hashlib.sha256(identity.encode()).hexdigest()
        if key in seen:
            continue
        total = float(offer['price_sar']) + float(offer['shipping_sar'])
        message = (f"🎁 VERIFIED SAUDI DEAL\n{offer['title']}\nMerchant: {offer['merchant']}\n"
                   f"Price: SAR {float(offer['price_sar']):.2f} + shipping SAR {float(offer['shipping_sar']):.2f}"
                   f" = SAR {total:.2f}\nRequirements: {offer['requirements']}\n"
                   f"Expires: {offer['expires_at']}\nOfficial link: {offer['official_url']}")
        send(message)
        seen.add(key)
        STATE.write_text(json.dumps(sorted(seen), indent=2) + '\n', encoding='utf-8')
        approved += 1
        if approved >= 5:
            break
    print(f'Sent {approved} verified alerts; rejected {rejected} incomplete/unverified entries.')


if __name__ == '__main__':
    main()
