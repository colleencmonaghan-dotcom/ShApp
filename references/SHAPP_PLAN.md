# ShApp - Project Plan
*Bio-first supermarket price comparison for Germany*

---

## What We Are Building

A web app where a user pastes a shopping list in any language or format, and gets back a ranked list of where to buy each item, prioritising the highest bio certification available at the lowest price. Target audience: bio-conscious shoppers in the Tübingen area, expanding to Germany.

---

## The Problem With Competitors

- **Supermarkt-Compare**: no shopping list upload, search one item at a time, bad UX
- **Smhaggle**: collapsing, 97% 1-star reviews on Trustpilot, not paying cashback
- Neither handles bio certification as a first-class feature

---

## Core Principles

1. Bio seal quality comes first, price second
2. User pastes a list in any format, the app figures out the rest
3. Prices must be live or clearly timestamped. Stale prices are worse than no prices.
4. Build for growth: nothing we build now gets thrown away later

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
| Scraping | Apify | Third-party scraping service with pre-built German supermarket scrapers |
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
│   └── content-checklist.md <- Fact-checking tracker
├── .env                    <- Secret API keys (never on GitHub)
├── .env.example            <- Template showing which keys are needed
└── pyproject.toml          <- List of installed libraries
```

---

## Build Phases

### Phase 1: Working Prototype (where we are now)
**Goal:** Prove the interface works end to end before tackling live data.

- [x] Project structure set up (Datalumina template)
- [x] Streamlit installed and running
- [x] Bio seals page built (Demeter, Bioland, EU-Bio explained)
- [x] Basic shopping list interface built
- [x] Manual CSV product database created (milk, eggs, butter - placeholder prices)
- [x] Anthropic library installed
- [x] API key in .env file
- [ ] Claude API matching: user types "milk" or "Milch" or "latte", Claude matches it to correct product in CSV
- [ ] Show all options per item in ranked table (best bio first, then alternatives)
- [ ] Add "last updated" timestamp to every price so users know how fresh data is

**Deliverable:** A working local app you can demo to friends in Tübingen for feedback.

---

### Phase 2: Content and Fact-Checking
**Goal:** Make sure everything we publish is accurate before going live.

- [ ] Verify all bio seal descriptions against Demeter.de, Bioland.de, Verbraucherzentrale
- [ ] Add Naturland seal (Netto BioBio partnership since Q3 2023)
- [ ] Update Lidl description to reflect Bioland partnership since 2018
- [ ] Expand product database manually to ~50 common items
- [ ] Add content-checklist.md source for every claim
- [ ] Write short "about" section explaining what ShApp is and who made it

**Deliverable:** Content that is defensible and sourced before anyone sees it publicly.

---

### Phase 3: Live Price Data (the hard part)
**Goal:** Replace static CSV prices with real, up-to-date prices from supermarkets.

**The data problem by store:**

| Store | Data available? | Method |
|---|---|---|
| Rewe | Yes, full online shop | Apify scraper |
| Edeka | Yes, full online shop | Apify scraper |
| Penny | Yes | Apify scraper |
| Kaufland | Yes | Apify scraper |
| Lidl | Partial - grocery prices not fully online | Weekly prospectus PDF + Apify |
| Aldi | Partial - no full online grocery shop | Weekly prospectus PDF via OCR |
| Reformhaus/Bioladen | No | Manual or not included |

**Steps:**
- [ ] Set up Apify account (apify.com, free tier available)
- [ ] Test Rewe scraper first (most reliable)
- [ ] Store results in Supabase database (replacing CSV)
- [ ] Set up GitHub Actions to run scraper every night at 2am
- [ ] Add "last updated" display in the app so users can see price freshness
- [ ] Handle Lidl and Aldi separately via PDF prospectus scraping

**Important:** Never show a price without showing when it was last checked. A price from 3 days ago should be flagged visually.

---

### Phase 4: Deploy Publicly
**Goal:** Put the app on the internet for real users.

- [ ] Create Streamlit Cloud account (streamlit.io, free)
- [ ] Connect to GitHub repository
- [ ] Add environment variables (API keys) to Streamlit Cloud settings
- [ ] Test everything works on the live URL
- [ ] Share with a small group of Tübingen friends first (soft launch)
- [ ] Add simple feedback form so users can report wrong prices or missing products

**Deliverable:** A public URL you can share.

---

### Phase 5: Growth (later)
**Goal:** Turn a useful tool into something people come back to.

- [ ] Recipe-to-shopping-list: user inputs a recipe, app builds the list and optimises it
- [ ] Weekly deals page: what is on sale this week at each store
- [ ] Price history: has this product gotten cheaper or more expensive over time
- [ ] Email/push alerts: "Demeter butter is on sale at Lidl this week"
- [ ] German translation of the entire app
- [ ] Mobile-optimised design
- [ ] Consider moving from Streamlit to a proper frontend (React) when Streamlit's limits become frustrating
- [ ] Potential monetisation: affiliate links, brand partnerships, premium features

---

## Immediate Next Steps (do these in order)

1. Finish Claude API matching in App.py (this is where we are right now)
2. Test with 10 different shopping list inputs, fix what breaks
3. Expand CSV to 50 products manually
4. Deploy to Streamlit Cloud so you have a real URL
5. Share with 5 people and collect feedback before building anything else

---

## Known Issues and Decisions Pending

- **Aldi and Lidl live prices**: not fully solvable without PDF scraping, which is complex. Consider launching without them and adding later.
- **Legal risk of scraping**: German law is grey on this. Existing competitors do it. Risk is tolerable at small scale but worth monitoring.
- **Language**: app currently in English, needs German translation before serious public launch.
- **Prices going stale**: critical trust issue. Every price must show a timestamp. Consider showing a warning if price is more than 48 hours old.

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
- Ask before adding scraping code, that is Phase 3 not now
