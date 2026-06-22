import streamlit as st
import pandas as pd
import anthropic
import json
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

st.set_page_config(page_title="ShApp - Bio Supermarkt Vergleich", layout="wide")

st.title("ShApp - Bio Supermarket Comparison")
st.write("Paste your shopping list and find the cheapest bio options near Tübingen.")

st.divider()

SEAL_ORDER = {"Demeter": 0, "Bioland": 1, "EU-Bio": 2}


def match_items_with_claude(items: list[str], products: list[str]) -> dict[str, str | None]:
    client = anthropic.Anthropic()
    product_list = "\n".join(f"- {p}" for p in products)
    items_list = "\n".join(f"- {item}" for item in items)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "Match each shopping list item to the best product from a German bio supermarket database.\n\n"
                    f"Shopping list (may be in any language):\n{items_list}\n\n"
                    f"Available products:\n{product_list}\n\n"
                    "Return ONLY a JSON object where each key is the EXACT shopping list item text "
                    "(including any quantities or extra words) and the value is the matched product name. "
                    'Example: {"2x milk": "Vollmilch 1L", "6 eggs": "Eier 6 Stück"}. '
                    "Use null if no match. No explanation, just JSON."
                ),
            }
        ],
    )

    try:
        import re
        text = message.content[0].text
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {item: None for item in items}
    except (json.JSONDecodeError, IndexError, KeyError, AttributeError):
        return {item: None for item in items}


def price_age_days(last_updated_str: str) -> int:
    updated = datetime.strptime(last_updated_str, "%Y-%m-%d").date()
    return (date.today() - updated).days


def show_results(df: pd.DataFrame, item_label: str, product_name: str) -> None:
    matches = df[df["product"] == product_name].copy()
    matches["seal_rank"] = matches["seal"].map(SEAL_ORDER).fillna(3)
    matches = matches.sort_values(["seal_rank", "price_eur"])

    best = matches.iloc[0]
    age = price_age_days(best["last_updated"])
    updated_label = f"checked {best['last_updated']}"

    if age > 2:
        st.warning(
            f"**{item_label.title()}** → {best['store']} | {best['brand']} | {best['seal']} | €{best['price_eur']:.2f} — ⚠️ price may be outdated ({updated_label})"
        )
    else:
        st.success(
            f"**{item_label.title()}** → {best['store']} | {best['brand']} | {best['seal']} | €{best['price_eur']:.2f} — {updated_label}"
        )

    with st.expander("See all options"):
        display = matches[["store", "brand", "seal", "price_eur", "last_updated", "notes"]].copy()
        display.columns = ["Store", "Brand", "Seal", "Price (€)", "Last Checked", "Notes"]
        st.dataframe(display, hide_index=True)


# --- SHOPPING LIST SECTION ---
st.header("Shopping List Optimizer")
st.write("Type or paste your shopping list below, one item per line.")

shopping_input = st.text_area(
    "Your shopping list", height=200, placeholder="Milk\nEggs\nButter\n..."
)

if st.button("Find best bio options", type="primary", disabled=not shopping_input):
    try:
        df = pd.read_csv("data/raw/products.csv")
    except FileNotFoundError:
        st.error("Product database not found. Make sure data/raw/products.csv exists.")
        st.stop()

    raw = shopping_input.replace(",", "\n")
    items = [line.strip() for line in raw.split("\n") if line.strip()]
    unique_products = df["product"].unique().tolist()

    with st.spinner("Matching items with Claude..."):
        matches = match_items_with_claude(items, unique_products)

    st.subheader("Results")
    for item in items:
        product_name = matches.get(item) or matches.get(item.lower())
        # Fallback: Claude may have normalised the key (e.g. stripped "2x" prefix)
        if not product_name:
            for key, val in matches.items():
                if key and (key.lower() in item.lower() or item.lower() in key.lower()):
                    product_name = val
                    break
        if not product_name or product_name not in df["product"].values:
            st.warning(f"No match found for: **{item}**")
        else:
            show_results(df, item, product_name)

st.divider()

# --- BIO SEALS SECTION ---
st.header("Understanding Bio Seals")
st.write(
    "Not all bio is equal. Here is what the labels actually mean, from strongest to weakest:"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("🌿 Demeter")
    st.write("**Strongest standard.**")
    st.write(
        "Goes far beyond organic farming. Requires biodynamic agriculture, animal welfare standards, and soil health practices. The gold standard in Germany."
    )
    st.write(
        "**Where to find it:** Reformhaus, Bioladen, some Rewe/Edeka shelves, weekly markets in Tübingen"
    )
    st.write("**Typical premium:** 20-40% above EU-Bio")

with col2:
    st.subheader("🌾 Bioland")
    st.write("**Strong standard.**")
    st.write(
        "Germany's largest organic association. Stricter than EU-Bio on animal welfare, no GMO, regional focus. A reliable choice."
    )
    st.write(
        "**Where to find it:** Rewe Bio, Edeka Bio, Lidl (official Bioland partner since 2018), some Aldi products"
    )
    st.write("**Typical premium:** 10-25% above EU-Bio")

with col3:
    st.subheader("☘️ EU-Bio")
    st.write("**Baseline standard.**")
    st.write(
        "The legal minimum to call something organic in Europe. No pesticides, no GMO. Solid but less strict than German associations on animal welfare and processing."
    )
    st.write(
        "**Where to find it:** Everywhere. Aldi GutBio, Lidl Bio, own-brand bio lines"
    )
    st.write("**Typical premium:** Starting point for comparison")

with col4:
    st.subheader("❓ No seal")
    st.write("**Unverified.**")
    st.write(
        "Some products use words like 'natürlich' or 'from the region' without any certification. These have no legal meaning in terms of organic standards."
    )
    st.write("**Where to find it:** Farmers markets, small producers, some packaging")
    st.write("**What to do:** Ask the seller directly")

st.divider()

st.subheader("The hidden secret: own-brand bio")
st.write("""
Around 65% of bio revenue in Germany now comes from supermarket own-brand lines like Aldi GutBio, 
Rewe Bio, and Edeka Bio. Many of these come from the same certified farms as expensive branded products. 
The difference is often just the label tier, not the farm. This app will help you find those hidden deals.
""")
