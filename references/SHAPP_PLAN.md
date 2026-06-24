# ShApp - Project Plan
*Bio-first supermarket price comparison for Germany*

---

## What We Are Building

A web app where a user pastes a shopping list in any language or format, and gets back a ranked list of where to buy each item, prioritising the highest bio certification available at the lowest price. Target audience: bio-conscious shoppers in the Tübingen area, expanding to Germany.

Scope includes both physical supermarkets and online bulk/bio shops, since a significant part of the target audience (vegan, bio-conscious) buys staples like legumes, nuts, grains and seeds online in bulk rather than in supermarkets.

---

## The Problem With Competitors

- **Supermarkt-Compare**: no shopping list upload, search one item at a time, bad UX
- **Smhaggle**: collapsing, 97% 1-star reviews on Trustpilot, not paying cashback
- Neither handles bio certification as a first-class feature
- Neither covers online bulk shops (KoRo, Süssundclever, Bode, Kamelur)

---

## Core Principles

1. Bio seal quality comes first, price second
2. User pastes a list in any format, the app figures out the rest
3. Prices must be live or clearly timestamped. Stale prices are worse than no prices.
4. Show both item price AND unit price (per 100g, per 100ml, or per unit for eggs etc.)
5. Build for growth: nothing we build now gets thrown away later

---

## Bio Seal Hierarchy (most to least strict)

| Seal | Standard | Typically found at |
|---|---|---|
| Demeter | Biodynamic, strictest | Reformhaus, Bioladen, Kaufland (250+ products), weekly markets |
| Bioland | German association, strict | Rewe, Edeka, Lidl (partner since 2018), Kaufland (partner since 2022), some Aldi |
| Naturland | German association, strict | Netto (BioBio line, partner since Q3 2023) |
| EU-Bio | Legal minimum, baseline | Everywhere - Aldi GutBio, Lidl Bio, K-Bio (Kaufland), own-brand lines |
| No seal | Unverified | Farmers markets, some small producers |

**Note on Kaufland:** Most complete for bio variety - carries EU-Bio (K-Bio own brand), Bioland (150+ K-Bio articles, partner since 2022), and Demeter (250+ products, member since 2020).

---

## Tech Stack

| Layer | Tool | What it is |
|---|---|---|
| Language | Python | Everything is Python |
| Interface | Streamlit | Turns Python into a webpage, no JavaScript needed |
| AI matching | Claude API (claude-sonnet-4-6) | Matches "milk" to "Vollmilch 1L" in any language |
| Package manager | uv | Installs Python libraries (Dave Ebbelaar's recommendation) |
| Database (phase 1) | CSV file | Simple spreadsheet, good enough to start |
| Database (phase 2) | Supabase | Free online database, replaces CSV when we have real data |
| Scraping - supermarkets | Apify | Third-party scraping service with pre-built German supermarket scrapers |
| Scraping - Shopify shops | Shopify products.json API | Free, no Apify needed, works for KoRo and Süssundclever |
| Scheduling | GitHub Actions | Runs scrapers every night for free |
| Hosting | Streamlit Cloud | Free, one click, connects to GitHub |
| Secrets | .env file | Stores API keys, never uploaded to GitHub |
| Project structure | Datalumina template | Dave Ebbelaar's standard folder structure |

---

## Folder Structure

```
ShApp/
├── App.py                  <- Main Streamlit app
├── data/
│   ├── raw/
│   │   └── products.csv    <- Manual product database (phase 1)
│   └── processed/          <- Cleaned data ready for use
├── src/
│   ├── matcher.py          <- Claude API matching logic
│   ├── scraper.py          <- Apify scraping logic (phase 3)
│   └── config.py           <- Settings and constants
├── references/
│   ├── SHAPP_PLAN.md       <- This file
│   └── content-checklist.md <- Fact-checking tracker
├── .env                    <- Secret API keys (never on GitHub)
├── .env.example            <- Template showing which keys are needed
└── pyproject.toml          <- List of installed libraries
```

---

## Product Data Structure

Every product in the database needs these fields:

| Field | Example | Notes |
|---|---|---|
| product | Vollmilch | Generic product name |
| category | dairy | For grouping and matching |
| store | Lidl | Store or shop name |
| brand | Bioland Milch | Brand or own-label name |
| seal | Bioland | Must be: Demeter, Bioland, Naturland, EU-Bio, or none |
| price_eur | 1.09 | Item price in euros |
| quantity | 1000 | Numeric quantity |
| unit | ml | g, ml, kg, l, or egg |
| last_checked | 2026-06-23 | Date price was verified |
| notes | Regional | Optional extra info |

Unit price is calculated automatically by the app: price / quantity * 100 for weight/volume, price / quantity for countable items.

---

## Build Phases

### Phase 1: Working Prototype (DONE)
**Goal:** Prove the interface works end to end before tackling live data.

- [x] Project structure set up (Datalumina template)
- [x] Streamlit installed and running
- [x] Bio seals page built (Demeter, Bioland, EU-Bio explained)
- [x] Basic shopping list interface built
- [x] Manual CSV product database created
- [x] Anthropic library installed and API key in .env
- [x] Claude API matching working (milk, Milch, typos all resolve correctly)
- [x] Unit pricing displayed (per 100g, per 100ml, per egg)
- [x] Results ranked by seal quality first, unit price second
- [x] Deployed to Streamlit Cloud
- [x] Shared with first testers, initial feedback collected

**Current live URL:** https://wdewnxgwrmcjaqnz4tcfnm.streamlit.app/

---

### Phase 2: Content and Fact-Checking (current focus)
**Goal:** Make sure everything we publish is accurate and the product database is broad enough to be useful.

- [ ] Verify all bio seal descriptions against Demeter.de, Bioland.de, Verbraucherzentrale
- [ ] Add Naturland seal to bio seals page (Netto BioBio partnership since Q3 2023)
- [ ] Update Kaufland description to reflect full bio picture (EU-Bio + Bioland + Demeter)
- [ ] Fix K-Bio seal entries in CSV: K-Bio is a brand name, not a certification. Use EU-Bio or Bioland as appropriate.
- [ ] Expand product database manually to ~50 common items
- [ ] Add "suggest a missing product" button so users can flag gaps
- [ ] Add visible disclaimer: prices are placeholder data, not live
- [ ] Write short "about" section explaining what ShApp is

**Priority products to add to CSV:**
Bread, chocolate, yoghurt, cheese, flour, oats, olive oil, apple juice, tomatoes, bananas, carrots, pasta, rice, coffee, oyster sauce, legumes (chickpeas, lentils, red beans), nuts (cashews, almonds, walnuts), nut butters, chia seeds, dried fruit

**Deliverable:** Content that is defensible and sourced before serious public sharing.

---

### Phase 3: Live Price Data
**Goal:** Replace static CSV prices with real, up-to-date prices.

#### Phase 3a: Online Shops (do first, easiest)

| Shop | What they sell | Platform | Method | Difficulty |
|---|---|---|---|---|
| KoRo (korodrogerie.de) | Bulk food, nuts, seeds, snacks | Shopify | products.json API | Very easy |
| Süssundclever (suessundclever.de) | Bulk bio food, sustainable packaging | Shopify | products.json API | Very easy |
| Bode Naturkost (bodenaturkost.de) | Direct importer, nuts/seeds/legumes/grains | Custom | Apify or price list PDF | Medium |
| Kamelur (kamelur.de) | Natural food + drugstore/household products | Custom | Apify or BeautifulSoup | Medium |

**How Shopify products.json works:**
Simply call `https://[shopname].de/products.json?limit=250` and you get all products, prices, weights and variants as clean structured data. No scraping HTML, no Apify needed. Free.

#### Phase 3b: Physical Supermarkets

| Store | Data available? | Method |
|---|---|---|
| Rewe | Yes, full online shop | Apify scraper |
| Edeka | Yes, full online shop | Apify scraper |
| Penny | Yes | Apify scraper |
| Kaufland | Yes | Apify scraper |
| Lidl | Partial - grocery prices not fully online | Weekly prospectus PDF + Apify |
| Aldi | Partial - no full online grocery shop | Weekly prospectus PDF via OCR |

**Steps for Phase 3:**
- [ ] Start with KoRo Shopify API (one afternoon of work)
- [ ] Add Süssundclever Shopify API
- [ ] Store results in Supabase database (replacing CSV)
- [ ] Set up GitHub Actions to run scrapers every night at 2am
- [ ] Add "last updated" display and visual warning if price is over 48 hours old
- [ ] Add Rewe via Apify
- [ ] Add Bode and Kamelur via Apify or BeautifulSoup
- [ ] Handle Lidl and Aldi via PDF prospectus (do last, most complex)

**Important:** Never show a price without showing when it was last checked.

---

### Phase 4: Public Launch
**Goal:** Put the app in front of real users properly.

- [x] Deploy to Streamlit Cloud
- [ ] Add disclaimer banner (prices are placeholder data)
- [ ] Add "suggest a missing product" form
- [ ] German translation of entire app
- [ ] Share with wider Tübingen audience
- [ ] Collect structured feedback (not just "it works")

---

### Phase 5: Growth
**Goal:** Turn a useful tool into something people come back to.

- [ ] Recipe-to-shopping-list: user inputs a recipe, app builds the list and optimises it
- [ ] Weekly deals page: what is on sale this week at each store
- [ ] Price history: has this product gotten cheaper or more expensive over time
- [ ] Email/push alerts: "Demeter butter is on sale at Lidl this week"
- [ ] Location awareness: which stores are near the user
- [ ] Mobile-optimised design
- [ ] Consider moving from Streamlit to a proper frontend (React) when limits become frustrating
- [ ] Potential monetisation: affiliate links, brand partnerships, premium features

---

## Known Issues and Decisions Pending

- **Aldi and Lidl live prices**: not fully solvable without PDF scraping. Launch without them and add later.
- **Legal risk of scraping**: German law is grey on this. Existing competitors do it. Risk is tolerable at small scale but worth monitoring.
- **Language**: app currently in English, needs German translation before serious public launch.
- **Prices going stale**: critical trust issue. Every price must show a timestamp. Flag prices over 48 hours old visually.
- **Reformhaus removed**: too inconsistent for price comparison. May revisit as a separate local shop category later.
- **Unit pricing edge cases**: bread, fresh produce and some items don't fit neatly into g/ml/egg categories. Handle case by case.

---

## Feedback Received So Far

- "It works" (tester 1)
- Suggestion: add closest location and travel distance (noted, Phase 5)
- Suggestion: be specific about weight and brand (addressed via unit pricing)
- Need: oyster sauce and other non-standard items not in CSV yet
- Vegan users buy bulk from KoRo, Süssundclever, Bode, Kamelur - these need to be in scope

---

## For Claude Code

When working on this project:
- Always read this file first for context
- The main app file is App.py in the project root
- Product data lives in data/raw/products.csv
- API keys are in .env, never hardcode them
- Use `uv add [library]` to install new packages, not pip
- Run the app with `uv run streamlit run App.py`
- The Claude API model to use is claude-sonnet-4-6
- Current phase is Phase 2: expanding product database and fixing content
- Do not add scraping code yet, that is Phase 3
- K-Bio is a brand name not a seal - seal column should say EU-Bio or Bioland
- Every product needs: product, category, store, brand, seal, price_eur, quantity, unit, last_checked, notes