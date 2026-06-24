import streamlit as st
import pandas as pd
import anthropic
import json
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv
from src.shopify_fetch import fetch_all_shops
from src.koro_fetch import fetch_koro

load_dotenv(Path(__file__).parent / ".env")


@st.cache_data(ttl=3600)
def load_live_data() -> pd.DataFrame:
    rows = []
    try:
        rows.extend(fetch_all_shops())
    except Exception:
        pass
    try:
        rows.extend(fetch_koro())
    except Exception:
        pass
    return pd.DataFrame(rows) if rows else pd.DataFrame()

st.set_page_config(page_title="ShApp - Bio Supermarkt Vergleich", layout="wide")

st.title("ShApp - Bio Supermarket Comparison")
st.write("Paste your shopping list and find the cheapest bio options near Tübingen.")

st.divider()

SEAL_ORDER = {"Demeter": 0, "Bioland": 1, "Naturland": 1, "EU-Bio": 2}


def match_items_with_claude(items: list[str]) -> dict[str, dict]:
    """Returns {input: {"term": "German keyword", "label": "Clean English label"}} for each item."""
    client = anthropic.Anthropic()
    items_list = "\n".join(f"- {item}" for item in items)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=768,
        messages=[
            {
                "role": "user",
                "content": (
                    "Translate each shopping list item into a short German keyword (1-3 words, no quantities) "
                    "suitable for searching a German bio supermarket product database. "
                    "Also provide a clean English display label, correcting any typos.\n\n"
                    f"Shopping list (may be in any language, may contain typos):\n{items_list}\n\n"
                    "Return ONLY a JSON object where each key is the EXACT shopping list item text. "
                    'Each value has "term" (German keyword) and "label" (clean English). '
                    'Example: {"egss": {"term": "Eier", "label": "Eggs"}, "2x milk": {"term": "Vollmilch", "label": "Milk"}, "cashews": {"term": "Cashewkerne", "label": "Cashews"}}. '
                    'Use {"term": null, "label": "<original>"} if no translation possible. No explanation, just JSON.'
                ),
            }
        ],
    )

    try:
        import re
        text = message.content[0].text
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {item: {"term": None, "label": item} for item in items}
    except (json.JSONDecodeError, IndexError, KeyError, AttributeError):
        return {item: {"term": None, "label": item} for item in items}


def price_age_days(last_checked_str: str) -> int:
    updated = datetime.strptime(last_checked_str, "%Y-%m-%d").date()
    return (date.today() - updated).days


def calc_unit_price(price: float, quantity: int, unit: str) -> tuple[float, str]:
    if unit == "g":
        return price / quantity * 100, "€/100g"
    elif unit == "ml":
        return price / quantity * 100, "€/100ml"
    elif unit == "egg":
        return price / quantity, "€/egg"
    else:
        return price / quantity, "€/piece"


def show_results(df: pd.DataFrame, item_label: str, search_term: str) -> None:
    matches = df[df["product"].str.contains(search_term, case=False, na=False)].copy()
    matches["seal_rank"] = matches["seal"].map(SEAL_ORDER).fillna(3)
    matches["unit_price"] = matches.apply(
        lambda r: calc_unit_price(r["price_eur"], r["quantity"], r["unit"])[0], axis=1
    )
    matches = matches.sort_values(["seal_rank", "unit_price"])

    best = matches.iloc[0]
    age = price_age_days(best["last_checked"])
    updated_label = f"checked {best['last_checked']}"
    up, up_label = calc_unit_price(best["price_eur"], best["quantity"], best["unit"])

    if age > 2:
        st.warning(
            f"**{item_label}** — {best['store']} | {best['brand']} | {best['seal']} | **€{best['price_eur']:.2f}** ⚠️ outdated ({updated_label})"
        )
    else:
        st.success(
            f"**{item_label}** — {best['store']} | {best['brand']} | {best['seal']} | **€{best['price_eur']:.2f}**"
        )
    st.caption(f"€{up:.2f} {up_label} · {updated_label}")

    with st.expander("See all options"):
        display = matches[["store", "brand", "seal", "price_eur", "unit_price", "last_checked", "notes"]].copy()
        display["unit_price"] = display.apply(
            lambda r: f"€{r['unit_price']:.2f} {calc_unit_price(r['price_eur'], matches.loc[r.name, 'quantity'], matches.loc[r.name, 'unit'])[1]}",
            axis=1
        )
        display.columns = ["Store", "Brand", "Seal", "Price (€)", "Unit Price", "Last Checked", "Notes"]
        st.dataframe(display, hide_index=True)


# --- SHOPPING LIST SECTION ---
st.header("Shopping List Optimizer")
st.write("Type or paste your shopping list below, one item per line.")

shopping_input = st.text_area(
    "Your shopping list", height=200, placeholder="Milk\nEggs\nButter\n..."
)

if st.button("Find best bio options", type="primary", disabled=not shopping_input):
    try:
        df_csv = pd.read_csv("data/raw/products.csv")
    except FileNotFoundError:
        st.error("Product database not found. Make sure data/raw/products.csv exists.")
        st.stop()

    df_live = load_live_data()
    df = pd.concat([df_csv, df_live], ignore_index=True) if not df_live.empty else df_csv

    if not df_live.empty:
        per_store = df_live.groupby("store").size().to_dict()
        breakdown = ", ".join(f"{s}: {n}" for s, n in per_store.items())
        st.caption(f"Live products loaded — {breakdown}")

    raw = shopping_input.replace(",", "\n")
    items = [line.strip() for line in raw.split("\n") if line.strip()]

    with st.spinner("Matching items with Claude..."):
        matches = match_items_with_claude(items)

    st.subheader("Results")
    for item in items:
        result = matches.get(item) or matches.get(item.lower())
        if not result:
            for key, val in matches.items():
                if key and (key.lower() in item.lower() or item.lower() in key.lower()):
                    result = val
                    break
        term = result.get("term") if result else None
        label = result.get("label", item) if result else item
        if not term or df["product"].str.contains(term, case=False, na=False).sum() == 0:
            st.warning(f"No match found for: **{label}**")
        else:
            show_results(df, label, term)

st.divider()

# --- BIO SEALS SECTION ---
st.header("Understanding Bio Seals")
st.write(
    "Not all bio is equal. Here is what the labels actually mean, from strongest to weakest:"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🌿 Demeter")
    st.write("**Strongest standard.**")
    st.write(
        "Biodynamic agriculture based on Rudolf Steiner's methods. Requires a minimum 10% of farm land set aside as a biodiversity preserve, nine biodynamic soil preparations, strict animal welfare, and integrated farm management. The gold standard in Germany."
    )
    st.write(
        "**Where to find it:** Bioladen, Naturkostladen, some Rewe and Edeka shelves, weekly markets in Tübingen"
    )
    st.write("**Typical premium:** noticeably higher than EU-Bio — exact difference varies by product")

with col2:
    st.subheader("🌾 Bioland")
    st.write("**Strong standard.**")
    st.write(
        "Germany's largest domestic organic association. Stricter than EU-Bio: more space per animal, at least half of feed must come from the farm itself, antibiotics strictly controlled, no GMO, strong regional focus."
    )
    st.write(
        "**Where to find it:** Rewe Bio, Edeka Bio, Lidl (partner since November 2018), Kaufland (partner since 2022)"
    )
    st.write("**Typical premium:** higher than EU-Bio — exact difference varies by product")

with col3:
    st.subheader("🍃 Naturland")
    st.write("**Strong international standard.**")
    st.write(
        "Germany's largest international organic association. Stricter than EU-Bio with mandatory annual animal welfare inspections on top of standard organic checks. Also covers social standards and fair trade principles."
    )
    st.write(
        "**Where to find it:** Netto (BioBio own-brand line, Naturland certified since late 2023)"
    )
    st.write("**Typical premium:** Similar to Bioland")

col4, col5, col6 = st.columns(3)

with col4:
    st.subheader("☘️ EU-Bio")
    st.write("**Baseline standard.**")
    st.write(
        "The legal minimum to call something organic in Europe. No synthetic pesticides, no GMO. Solid but less strict than German associations on animal welfare, feed sourcing, and processing."
    )
    st.write(
        "**Where to find it:** Everywhere — Aldi GutBio, Lidl Bio, Kaufland K-Bio, own-brand bio lines across all major supermarkets"
    )
    st.write("**Typical premium:** Starting point for comparison")

with col5:
    st.subheader("🛒 K-Bio (Kaufland)")
    st.write("**Store own-label brand, not a certification.**")
    st.write(
        "K-Bio is Kaufland's own-brand name for organic products. The underlying certification is EU-Bio. Kaufland is also one of the most complete bio supermarkets in Germany — it carries EU-Bio (K-Bio), Bioland (partner since 2022, 150+ products), and Demeter (member since 2020, 250+ products)."
    )
    st.write(
        "**Where to find it:** Kaufland stores only"
    )
    st.write("**Tip:** Check the small print — a Kaufland product can carry Bioland or Demeter, not just K-Bio")

with col6:
    st.subheader("❓ No seal")
    st.write("**Unverified.**")
    st.write(
        "Words like 'natürlich', 'from the region', or 'traditional' have no legal meaning in terms of organic standards. Any producer can use them without certification."
    )
    st.write("**Where to find it:** Farmers markets, small producers, some packaging")
    st.write("**What to do:** Ask the seller directly about their farming practices")

st.divider()

st.subheader("The hidden secret: own-brand bio")
st.write("""
Every major German supermarket now has its own bio line — Aldi GutBio, Rewe Bio, Edeka Bio, Lidl Bio.
Many of these come from the same certified farms as expensive branded products.
The difference is often just the label, not the farm. This app will help you find those hidden deals.
""")

st.divider()

st.header("About")
st.write("""
I'm Irish, living just outside Tübingen.

When I moved to Germany I noticed two things: bio products are everywhere, and nobody makes it easy
to figure out which ones are actually worth buying.

The bio labels confused me at first. Is "EU-Bio" just a checkbox, or does it mean something? Is Demeter
genuinely different, or is it marketing? I wanted straight answers, not greenwashing.

I also wanted to know where to shop. There are apps that collect the weekly supermarket magazines, but
you still end up scrolling through pages of deals. I wanted one place to ask "what does milk cost this
week, and where?" — and eventually, "should I wait for a sale, or is today's price already good?"

ShApp started as a price comparison tool. The bio ranking is a bonus — because once I understood what
the seals actually mean, I wanted to factor that in too. But this is fundamentally about prices.
Salaries haven't kept up with inflation, and nobody should be paying more than they have to for their
weekly shop.

This is version one. Weekly sale prices are coming. More stores are coming. For now: paste your list,
see your options.
""")
