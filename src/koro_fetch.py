import requests
from datetime import date

# Public access key found in KoRo's own storefront HTML
_KORO_KEY = "SWSCTNNXAGVLUVDQDHNCCVFQQW"
_BASE = "https://www.korodrogerie.de/store-api"
_MAX_PAGES = 5  # 500 products covers the main bio catalogue

_SEAL_KEYWORDS = {
    "Demeter": ["demeter"],
    "Bioland": ["bioland"],
    "Naturland": ["naturland"],
    "EU-Bio": ["bio"],
}

_CATEGORY_KEYWORDS = {
    "nuts": ["kerne", "nuss", "nüsse", "mandel", "cashew", "pistazie", "pecan", "walnuss", "haselnuss", "erdnuss"],
    "spreads": ["mus", "aufstrich", "tahini", "tahin"],
    "dried fruit": ["trocken", "rosine", "dattel", "feige", "aprikose", "pflaume", "mango"],
    "grains": ["reis", "hafer", "quinoa", "buchweizen", "dinkel", "teff", "getreide"],
    "baking": ["mehl", "zucker", "backpulver"],
    "pasta": ["nudeln", "pasta", "spaghetti"],
    "oil": ["öl", "ol"],
    "snacks": ["schokolade", "cookie", "chips", "riegel"],
    "sauces": ["sauce", "soße", "pesto"],
    "superfoods": ["chia", "hanf", "matcha", "spirulina", "moringa", "maca"],
    "pulses": ["linsen", "kichererbsen", "bohnen", "erbsen"],
    "spices": ["gewürz", "salz", "pfeffer"],
    "cereals": ["müsli", "granola"],
}

_BIO_FILTER = {
    "type": "multi",
    "operator": "or",
    "queries": [
        {"type": "contains", "field": "name", "value": "Bio"},
        {"type": "contains", "field": "name", "value": "Demeter"},
        {"type": "contains", "field": "name", "value": "Bioland"},
        {"type": "contains", "field": "name", "value": "Naturland"},
    ],
}


def _detect_seal(name: str) -> str | None:
    text = name.lower()
    for seal, keywords in _SEAL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return seal
    return None


def _detect_category(name: str) -> str:
    text = name.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat
    return "other"


def _convert_unit(purchase_unit: float, unit_code: str) -> tuple[int, str] | None:
    uc = unit_code.lower()
    if uc == "kg":
        return int(purchase_unit * 1000), "g"
    if uc == "g":
        return int(purchase_unit), "g"
    if uc == "l":
        return int(purchase_unit * 1000), "ml"
    if uc == "ml":
        return int(purchase_unit), "ml"
    if uc in ("stk", "stück", "st"):
        return int(purchase_unit), "piece"
    return None


def fetch_koro() -> list[dict]:
    headers = {
        "sw-access-key": _KORO_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    rows = []
    seen_ids: set[str] = set()
    today = date.today().isoformat()

    for page in range(_MAX_PAGES):
        try:
            resp = requests.post(
                f"{_BASE}/product",
                headers=headers,
                json={"limit": 100, "offset": page * 100, "filter": [_BIO_FILTER]},
                timeout=20,
            )
            resp.raise_for_status()
            batch = resp.json().get("elements", [])
        except Exception:
            break

        if not batch:
            break

        new_in_batch = 0
        for p in batch:
            pid = p.get("id", "")
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            new_in_batch += 1

            if not p.get("active"):
                continue

            name = p.get("name", "")
            seal = _detect_seal(name)
            if not seal:
                continue

            calc = p.get("calculatedPrice") or {}
            price = calc.get("totalPrice") or calc.get("unitPrice")
            if not price or price <= 0:
                continue

            unit_obj = p.get("unit") or {}
            unit_code = unit_obj.get("shortCode", "")
            purchase_unit = p.get("purchaseUnit")
            if not purchase_unit or not unit_code:
                continue

            converted = _convert_unit(float(purchase_unit), unit_code)
            if not converted:
                continue
            quantity, unit = converted
            if quantity <= 0:
                continue

            price_f = round(float(price), 2)
            # Sanity check: skip obviously wrong prices (unit price > €200/100g is a data error)
            if unit in ("g", "ml") and price_f / quantity * 100 > 200:
                continue

            rows.append({
                "product": name,
                "category": _detect_category(name),
                "store": "KoRo",
                "brand": "KoRo",
                "seal": seal,
                "price_eur": price_f,
                "quantity": quantity,
                "unit": unit,
                "last_checked": today,
                "notes": "",
            })

        # Stop paginating if all products on this page were already seen (API cycled)
        if new_in_batch == 0:
            break
        if len(batch) < 100:
            break

    return rows
