import re
import requests
from datetime import date

SHOPS = {
    "Süssundclever": "https://www.suessundclever.de/products.json",
}

SEAL_KEYWORDS = {
    "Demeter": ["demeter"],
    "Bioland": ["bioland"],
    "Naturland": ["naturland"],
    "EU-Bio": ["bio", "organic", "ökologisch", "okologisch"],
}

CATEGORY_MAP = {
    "Nüsse & Kerne": "nuts",
    "Nüsse_Kerne_Samen": "nuts",
    "Trockenfrüchte": "dried fruit",
    "Trockfrüchte": "dried fruit",
    "Hülsenfrüchte": "pulses",
    "Getreide": "grains",
    "Mehl": "baking",
    "Koch- und Backzutaten": "baking",
    "Öle": "oil",
    "Aufstriche": "spreads",
    "Schokolade": "snacks",
    "Snacks & Naschen": "snacks",
    "Müsli": "cereals",
    "Cerealien": "cereals",
    "Pasta": "pasta",
    "Reis": "grains",
    "Gewürze": "spices",
    "Superfoods": "superfoods",
    "Milchprodukte": "dairy",
    "Eier": "eggs",
}

_WEIGHT_RE = [
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*kg", re.I), "kg"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*g\b", re.I), "g"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*l\b", re.I), "l"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*ml", re.I), "ml"),
]


def _detect_seal(title: str, tags: list[str]) -> str | None:
    text = (title + " " + " ".join(tags)).lower()
    for seal, keywords in SEAL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return seal
    return None


def _parse_weight(weight: float, weight_unit: str) -> tuple[int, str]:
    if weight_unit == "kg":
        return int(weight * 1000), "g"
    if weight_unit == "l":
        return int(weight * 1000), "ml"
    if weight_unit == "ml":
        return int(weight), "ml"
    return int(weight), "g"


def _weight_from_title(title: str) -> tuple[int, str] | None:
    for pattern, unit in _WEIGHT_RE:
        m = pattern.search(title)
        if m:
            val = float(m.group(1).replace(",", "."))
            return _parse_weight(val, unit)
    return None


def _category_from_tags(tags: list[str]) -> str:
    for tag in tags:
        if tag in CATEGORY_MAP:
            return CATEGORY_MAP[tag]
        for key, cat in CATEGORY_MAP.items():
            if key.lower() in tag.lower():
                return cat
    return "other"


def fetch_shop(store_name: str, url: str) -> list[dict]:
    rows = []
    today = date.today().isoformat()
    page = 1

    while True:
        try:
            resp = requests.get(url, params={"limit": 250, "page": page}, timeout=15)
            resp.raise_for_status()
            batch = resp.json().get("products", [])
        except Exception:
            break

        if not batch:
            break

        for p in batch:
            tags = [t for t in p.get("tags", [])]
            title = p.get("title", "")
            seal = _detect_seal(title, tags)
            if not seal:
                continue

            category = CATEGORY_MAP.get(p.get("product_type", ""), None) or _category_from_tags(tags)

            for v in p.get("variants", []):
                try:
                    price = float(v.get("price", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if price <= 0:
                    continue

                grams = v.get("grams") or v.get("weight")
                if grams:
                    quantity, unit = int(grams), "g"
                else:
                    extracted = _weight_from_title(title)
                    if not extracted:
                        continue
                    quantity, unit = extracted

                if quantity <= 0:
                    continue

                variant_title = v.get("title", "")
                name = f"{title} — {variant_title}" if variant_title not in ("", "Default Title") else title

                rows.append({
                    "product": name,
                    "category": category,
                    "store": store_name,
                    "brand": store_name,
                    "seal": seal,
                    "price_eur": round(price, 2),
                    "quantity": quantity,
                    "unit": unit,
                    "last_checked": today,
                    "notes": "",
                })

        page += 1
        if len(batch) < 250:
            break

    return rows


def fetch_all_shops() -> list[dict]:
    rows = []
    for store_name, url in SHOPS.items():
        rows.extend(fetch_shop(store_name, url))
    return rows
