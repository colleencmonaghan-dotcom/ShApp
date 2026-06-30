"""
Rewe live bio product fetcher.

Uses Playwright (stealth mode) to bypass Cloudflare WAF:
  1. Navigate to shop.rewe.de
  2. Accept cookies
  3. Enter PLZ 72070 (Tuebingen)
  4. Click Abholservice → select Schleifmuehleweg store
  5. Search each category term, parse product tiles

Sync Playwright API is used so this works inside Streamlit (no asyncio conflict).
"""
import csv
import re
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

_CSV_PATH = Path(__file__).parent.parent / "data" / "raw" / "rewe_products.csv"

_MARKET_PLZ = "72070"

_SEARCH_TERMS = [
    "Bio Milch",
    "Bio Joghurt",
    "Bio Butter",
    "Bio Käse",
    "Bio Eier",
    "Bio Brot",
    "Bio Müsli",
    "Bio Haferflocken",
    "Bio Öl",
    "Bio Pasta",
    "Bio Reis",
    "Bio Gemüse",
    "Bio Obst",
]

_SEAL_KEYWORDS = {
    "Demeter": "Demeter",
    "Bioland": "Bioland",
    "Naturland": "Naturland",
}

_CATEGORY_MAP = {
    "milch": "dairy", "joghurt": "dairy", "quark": "dairy", "sahne": "dairy",
    "käse": "dairy", "butter": "dairy", "schmand": "dairy",
    "eier": "eggs",
    "brot": "bread", "brötchen": "bread",
    "müsli": "cereals", "haferflocken": "cereals", "cornflakes": "cereals",
    "pasta": "pasta", "nudeln": "pasta",
    "reis": "rice",
    "öl": "oils", "olivenöl": "oils",
    "gemüse": "vegetables", "tomate": "vegetables", "karotte": "vegetables",
    "obst": "fruit", "apfel": "fruit", "banane": "fruit",
    "hafer": "plant-based", "soja": "plant-based", "mandel": "plant-based",
    "kokos": "plant-based", "drink": "plant-based",
    "schokolade": "snacks", "keks": "snacks", "cookie": "snacks",
    "kaffee": "coffee-tea", "tee": "coffee-tea",
}


def _detect_seal(name: str) -> str:
    lower = name.lower()
    for keyword, seal in _SEAL_KEYWORDS.items():
        if keyword.lower() in lower:
            return seal
    if "bio" in lower:
        return "EU-Bio"
    return ""


def _guess_category(name: str) -> str:
    lower = name.lower()
    for keyword, cat in _CATEGORY_MAP.items():
        if keyword in lower:
            return cat
    return "other"


def _parse_brand(name: str) -> str:
    # REWE Bio products → "REWE Bio"; everything else → first word
    if name.lower().startswith("rewe bio"):
        return "REWE Bio"
    if name.lower().startswith("rewe"):
        return "REWE"
    parts = name.split()
    return parts[0] if parts else ""


def _parse_price(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r'[^\d,]', '', raw).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_quantity_unit(grammage: str) -> tuple[int | None, str | None]:
    """
    '200g (1 kg = 5,75 €)' → (200, 'g')
    '1l'                   → (1000, 'ml')
    '1lzzgl. 0,15 € Pfand' → (1000, 'ml')
    '6 Stück'              → (6, 'piece')
    """
    if not grammage:
        return None, None
    # Strip deposit info
    grammage = re.sub(r'zzgl\..*', '', grammage, flags=re.IGNORECASE)
    # Strip parenthetical unit-price clause
    grammage = re.sub(r'\(.*?\)', '', grammage)
    grammage = grammage.strip()

    m = re.match(r'([\d,\.]+)\s*(g|ml|l|kg|stk|stück|stücke|piece)', grammage, re.IGNORECASE)
    if not m:
        return None, None

    qty_str = m.group(1).replace(',', '.')
    unit_raw = m.group(2).lower()

    try:
        qty = float(qty_str)
    except ValueError:
        return None, None

    if unit_raw == 'kg':
        return int(qty * 1000), 'g'
    if unit_raw == 'l':
        return int(qty * 1000), 'ml'
    if unit_raw in ('stk', 'stück', 'stücke', 'piece'):
        return int(qty), 'piece'
    return int(qty), unit_raw


def _parse_tiles(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    tiles = [el for el in soup.select('[id^=plr-]')
             if re.fullmatch(r'plr-\d+', el.get('id', ''))]

    rows = []
    today = str(date.today())
    for tile in tiles:
        pid = tile.get('id').replace('plr-', '')
        title_el = tile.find(id=f'plr-{pid}-title')
        price_el = tile.find(id=f'plr-{pid}-price')
        grammage_el = tile.find(id=f'plr-{pid}-grammage')

        name = title_el.get_text(strip=True) if title_el else None
        if not name or 'bio' not in name.lower():
            continue

        price = _parse_price(price_el.get_text(strip=True) if price_el else '')
        if price is None or price <= 0:
            continue

        grammage = grammage_el.get_text(strip=True) if grammage_el else ''
        quantity, unit = _parse_quantity_unit(grammage)
        if quantity is None or quantity <= 0:
            continue

        rows.append({
            'product': name,
            'category': _guess_category(name),
            'store': 'Rewe',
            'brand': _parse_brand(name),
            'seal': _detect_seal(name),
            'price_eur': price,
            'quantity': quantity,
            'unit': unit,
            'last_checked': today,
            'notes': '',
        })
    return rows


def _select_market(page) -> bool:
    """Go through the PLZ → Abholservice → Tuebingen store selection flow."""
    import time

    page.goto("https://shop.rewe.de", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)

    try:
        page.click("button[data-testid='uc-accept-all-button']", timeout=5000)
        time.sleep(1)
    except Exception:
        pass
    time.sleep(2)

    try:
        postal = page.wait_for_selector("input[placeholder='51063']", timeout=10000, state="visible")
        postal.click(click_count=3)
        page.keyboard.press("Control+a")
        postal.type(_MARKET_PLZ, delay=80)
        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(3)
    except Exception as e:
        raise RuntimeError(f"Rewe: PLZ input not found: {e}")

    try:
        page.click("button.gbmc-qa-pickup-trigger", timeout=8000)
        time.sleep(3)
    except Exception as e:
        raise RuntimeError(f"Rewe: Abholservice button not found: {e}")

    try:
        market_items = page.locator(".gbmc-market-list-item")
        picker = market_items.first.locator("[data-testid='gbmc-market-picker']")
        picker.click(force=True, timeout=8000)
        time.sleep(5)
    except Exception as e:
        raise RuntimeError(f"Rewe: Market picker not found: {e}")

    return True


def _search_and_parse(page, term: str) -> list[dict]:
    import time

    try:
        search = page.wait_for_selector("input[type='search']", timeout=10000, state="visible")
        search.click(click_count=3)
        page.keyboard.press("Control+a")
        search.type(term, delay=60)
        page.keyboard.press("Enter")
        time.sleep(4)
    except Exception as e:
        print(f"Rewe: search for {term!r} failed: {e}")
        return []

    html = page.content()
    rows = _parse_tiles(html)
    print(f"Rewe: '{term}' -> {len(rows)} bio products")
    return rows


def _save_to_csv(rows: list[dict]) -> None:
    """Save fetched products to CSV for Streamlit Cloud fallback."""
    if not rows:
        return
    _CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Rewe: saved {len(rows)} products to {_CSV_PATH}")


def load_rewe_from_csv() -> list[dict]:
    """
    Load Rewe products from pre-fetched CSV.
    Used on Streamlit Cloud where headful browser is unavailable.
    """
    if not _CSV_PATH.exists():
        return []
    rows = []
    with open(_CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["price_eur"] = float(row["price_eur"])
                row["quantity"] = int(row["quantity"])
            except (ValueError, KeyError):
                continue
            rows.append(row)
    print(f"Rewe: loaded {len(rows)} products from CSV cache")
    return rows


def fetch_rewe() -> list[dict]:
    """
    Fetch live Rewe bio products for Tuebingen store via Playwright stealth.

    Requires a display (headless=False) because Cloudflare Turnstile blocks
    headless browsers on the product catalog pages. Works on local machines.
    On Streamlit Cloud, the try/except in load_live_data() falls back to
    load_rewe_from_csv() which reads the last locally-generated CSV.

    Returns rows in the same format as fetch_all_shops() and fetch_koro().
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        Stealth().apply_stealth_sync(page)

        _select_market(page)

        seen: set[str] = set()
        all_rows: list[dict] = []

        for term in _SEARCH_TERMS:
            rows = _search_and_parse(page, term)
            for row in rows:
                key = row["product"]
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)

        browser.close()

    print(f"Rewe: {len(all_rows)} unique bio products total")
    _save_to_csv(all_rows)
    return all_rows
