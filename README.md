# Blitz Console — Apollo-style local prospecting UI

Streamlit app + Python pipeline for the [Blitz API](https://blitz-api.ai). Build filtered ICP searches with live result counts, run them in the background, get SalesHandy-ready CSVs out.

## Quickstart

```bash
# 1. Install deps (one time)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Install pre-commit hook (blocks accidental API-key commits)
bash scripts/install-hooks.sh

# 3. Set API key (writes to .env, gitignored)
echo "BLITZ_API_KEY=blitz-..." > .env

# 4. Launch
.venv/bin/streamlit run app/Home.py
# → opens http://localhost:8501
```

## Secret hygiene

- `.env` (real API key) is gitignored
- `.env.example` (template with placeholder) is committed
- `scripts/install-hooks.sh` installs a local pre-commit hook that refuses to commit any file containing a real Blitz API key (matches `blitz-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` shape with hex chars)
- The hook also blocks `.env`, `blitz.db`, and `.claude/settings.local.json` from ever being staged
- GitHub's built-in secret scanning is enabled by default on public repos as a second line of defense

## Pages

| Page | Purpose |
|---|---|
| **Home** | Credit balance, recent runs, saved ICPs at a glance |
| **Build Search** | Apollo-style filter panel (14 supported filters), live count preview (1 cr/refresh), cost estimator, save as ICP, run now |
| **Saved ICPs** | List/clone/rename/delete saved filter profiles |
| **Run History** | Live progress for in-flight runs, CSV downloads for completed runs |
| **Lookup Tools** | Single-shot Blitz endpoint utilities (employee finder, reverse email, company enrich) |
| **Settings** | API key management, credit-balance history chart |

## Filter coverage (what Blitz actually supports)

**Company:** industry (534-value enum, include/exclude) · employee size (numeric range OR 8 buckets) · founded year range · HQ country/city/continent/sales region · description keywords (include/exclude) · company type · min LinkedIn followers · company name (include/exclude) · LinkedIn URL match.

**People:** job title (include/exclude, keyword OR `[exact]`, optional headline search) · seniority/level (C-Team, VP, Director, Manager, Staff, Other) · department/function (22 values) · location country/city/continent/sales region · min LinkedIn connections.

**Apollo features Blitz doesn't expose** (intentionally not in the UI): revenue · funding · technographics · job postings · department headcount · NAICS/SIC · state-level geography · years in role · years experience · past companies · education/skills · email-status pre-filter · LinkedIn activity recency.

## Architecture

```
app/
├── Home.py                       streamlit run target
├── pages/                        sidebar-nav pages
├── components/filter_panel.py    14-filter panel (sidebar)
├── lib/
│   ├── blitz_client.py           thin Blitz API wrapper
│   ├── filter_model.py           SearchFilters/RunOptions dataclasses ↔ JSON ↔ widgets
│   ├── db.py                     SQLite (icps, runs, credit_log, count_cache)
│   ├── runner.py                 spawns blitz_pipeline.py as subprocess
│   └── reference_data.py         loads JSON enums
└── data/                         industries, functions, levels, countries (JSON)
blitz_pipeline.py                 the search/enrich/csv pipeline (resumable)
blitz.db                          SQLite (gitignored)
runs/run_NNNNNN/                  per-run dir: filters.json, log, raw, enriched, csv
```

The Streamlit UI never blocks on long jobs — clicking **Run** spawns
`blitz_pipeline.py` as a subprocess that survives Streamlit reruns. The
**Run History** page polls the run's log + DB row to show live progress.

## Cost model (empirical, verified)

- Search (`/v2/search/people`): **1 credit per result returned**
  - With `max_results: 1`, you get the `total_results` count for **1 credit** — that's how the live preview works
- Email enrich (`/v2/enrichment/email`): **1 credit per attempt**, regardless of hit/miss
- Account info: free
- Rate limit: 5 rps (script throttles to 4 rps)

## Original CLI (still works)

```bash
BLITZ_API_KEY=... python3 blitz_pipeline.py search \
  --out leads_raw.json --target 700 --pages-per-tier 3 \
  --per-company 2 --max-credits 1200

BLITZ_API_KEY=... python3 blitz_pipeline.py enrich \
  --in leads_raw.json --out leads_enriched.json --max-credits 2800

python3 blitz_pipeline.py csv --in leads_enriched.json \
  --out leads_for_saleshandy.csv --email-only
```

---

## First run that produced this codebase

Sourced via [Blitz API](https://blitz-api.ai) on 2026-05-01.

## Filters applied
- **Industry:** `Software Development` OR `IT Services and IT Consulting`
- **Company size:** 20–100 employees
- **Job-title cascade (priority order):** Founder → CEO → VP (Marketing/Growth/Sales/CAC) → Director → Head of → Manager
- **Per company cap:** 2 leads max
- **Geography:** worldwide (no country filter)

## Output files

| File | Contents | Use for |
|---|---|---|
| `leads_for_saleshandy.csv` | Rows where Blitz returned a verified work email | Direct import into SalesHandy |
| `leads_all.csv` | All sourced leads incl. those without an email | Reference / future re-enrichment |
| `leads_raw.json` | Deduped raw API records | Re-running enrichment / debugging |
| `leads_raw.json.raw` | Complete pre-dedupe pages, by tier | Resume search if needed |
| `leads_enriched.json` | Per-lead email enrichment responses | Audit / re-export CSV |

## CSV columns

| Column | Source | Notes |
|---|---|---|
| First Name / Last Name | `first_name` / `last_name` from Blitz | Already split, no need to clean |
| Email | `/v2/enrichment/email` `email` field | Verified by Blitz's internal waterfall (Hunter, Findymail, etc.). Empty when not found. |
| Company Name | current `experiences[0].company_name` | |
| Company Industry | filter value: `Software Development / IT Services and IT Consulting` | Filter constraint, not per-company. To get exact per-company industry, run `/v2/enrichment/company` (extra credits). |
| Company Employee Size | filter value: `20-100` | Same as above — filter range, not per-company. |
| Job Title | current `experiences[0].job_title` (falls back to LinkedIn `headline`) | |
| LinkedIn URL | person `linkedin_url` | |
| Tier Matched | which priority tier surfaced this lead | `founder` is highest, `manager` lowest |

## Pipeline

```bash
# 1. Search across 6 priority tiers, dedupe to ≤2 per company
BLITZ_API_KEY=... python3 blitz_pipeline.py search \
  --out leads_raw.json --target 700 --pages-per-tier 3 \
  --per-company 2 --max-credits 1200

# 2. Enrich emails in priority order with hard credit cap
BLITZ_API_KEY=... python3 blitz_pipeline.py enrich \
  --in leads_raw.json --out leads_enriched.json --max-credits 2800

# 3. Output two CSVs
python3 blitz_pipeline.py csv --in leads_enriched.json \
  --out leads_for_saleshandy.csv --email-only
python3 blitz_pipeline.py csv --in leads_enriched.json \
  --out leads_all.csv
```

Both `search` and `enrich` are **resumable** — they persist incrementally and skip work that's already in the output file, so a kill mid-run only loses the in-flight call.

## Cost model (empirical, 2026-05-01)

- Find People search: **1 credit per result returned**
- Email enrichment: **1 credit per attempt**, regardless of hit/miss (despite docs saying "1 per found")
- Account info GET: appears to be free
- Rate limit: 5 rps (script throttles to 4 rps)
