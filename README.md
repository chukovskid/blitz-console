# Blitz Console

A local-first prospecting UI on top of the [Blitz API](https://blitz-api.ai) — Apollo-style filters, live result counts, runs in the background, exports SalesHandy-ready CSVs.

Built because the official API has no console for ICP exploration. Lets you tune filters and see the result count change *before* spending credits on a real run.

![Build Search screenshot — see app/pages/1_Build_Search.py](https://img.shields.io/badge/built_with-Streamlit_1.57-FF4B4B?logo=streamlit) ![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Two ways to use this

### A. Run locally (recommended for real searches)

```bash
git clone https://github.com/chukovskid/blitz-console.git
cd blitz-console

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

bash scripts/install-hooks.sh         # blocks accidental key commits

cp .env.example .env
# then open .env and paste your real Blitz API key

.venv/bin/streamlit run app/Home.py
# → opens http://localhost:8501
```

Need a Blitz API key? Get one at https://blitz-api.ai. Free trial includes ~10k credits.

### B. Use the hosted version

If a Streamlit Cloud deployment exists, ask the project owner for the URL + password. The hosted version is password-gated via the `BLITZ_CONSOLE_PASSWORD` env var.

> **State doesn't persist between hosted-app restarts** (Streamlit Cloud has ephemeral disk on the free tier). For real runs whose history you want to keep — saved ICPs, enriched leads, CSVs — run locally.

---

## What's in the UI

| Page | What it does |
|---|---|
| **🏠 Home** | Credit balance, recent runs, saved ICPs at a glance |
| **🎯 Build Search** | Apollo-style filter panel with all 14 supported Blitz filters · live total-results count (1 cr per refresh, cached) · cost estimator · save filters as a named ICP · click Run |
| **📚 Saved ICPs** | List / load / clone / rename / delete filter profiles |
| **📜 Run History** | Live progress for in-flight runs · CSV downloads when done · cancel button |
| **🔍 Lookup Tools** | Single-shot calls: employee finder · reverse email · email/phone/company enrichment |
| **⚙️ Settings** | Update API key · credit-balance history chart |

## Filter coverage (vs Apollo / Clay)

**Blitz supports** (all in the UI):

- *Company:* industry (534-value enum, include/exclude) · size (numeric range OR 8 buckets) · founded year range · HQ country/city/continent/sales region · description keywords (include/exclude) · type (public/private/etc) · min LinkedIn followers · name (include/exclude) · LinkedIn URL match
- *People:* job title (include/exclude, keyword OR `[exact]`, optional headline search) · seniority (C-Team, VP, Director, Manager, Staff, Other) · function/department (22 values) · location country/city/continent/sales region · min LinkedIn connections

**Blitz does NOT support** (intentionally hidden so the UI doesn't lie):

revenue · funding / last round · technographics · current job postings · department headcount · NAICS/SIC · state-level geography · years in role · years experience · past companies · education / skills · email-status pre-filter · LinkedIn activity recency

## Cost model (verified empirically)

| Operation | Cost |
|---|---|
| `/v2/search/people` (count + actual search) | **1 credit per result returned**. With `max_results: 1` you get `total_results` for 1 credit — that's how the live preview works. |
| `/v2/enrichment/email` | **1 credit per attempt**, regardless of hit/miss (Blitz docs say "1 per found" but observed differently). |
| `/v2/account/key-info` | Free |
| Rate limit | 5 req/sec (script throttles to 4) |

Empirical email hit rate: ~58% on Software Development / IT Services / 20–100 employee companies.

A typical 1,000-lead-with-emails run uses ~1,700 credits.

---

## Architecture

```
app/
├── Home.py                       streamlit entry point
├── pages/                        sidebar-nav pages
├── components/filter_panel.py    14-filter sidebar component
├── lib/
│   ├── blitz_client.py           thin Blitz API wrapper
│   ├── filter_model.py           SearchFilters/RunOptions ↔ JSON ↔ widgets
│   ├── db.py                     SQLite (icps, runs, credit_log, count_cache)
│   ├── runner.py                 spawns blitz_pipeline.py as subprocess
│   ├── auth.py                   optional password gate (BLITZ_CONSOLE_PASSWORD)
│   └── reference_data.py         loads industry/function/level/country JSON
└── data/                         enums for the filter panel

blitz_pipeline.py                 search → enrich → csv pipeline (resumable, persists per page)
blitz.db                          SQLite (local, gitignored)
runs/run_NNNNNN/                  per-run dir: filters.json, log, raw json, enriched json, CSVs
```

The Streamlit UI never blocks on long jobs — clicking **Run** spawns `blitz_pipeline.py` as a separate process that survives Streamlit reruns. **Run History** polls the log file + DB row for live progress.

## Secret hygiene

- Real key lives in `.env` (gitignored). `.env.example` is the committed template.
- Pre-commit hook (`scripts/install-hooks.sh`) refuses to stage anything that looks like a real Blitz key (`blitz-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` hex shape) and refuses to stage `.env`, `blitz.db`, or `.claude/settings.local.json` even when explicitly forced.
- `BLITZ_CONSOLE_PASSWORD` env var enables a password gate on every page — recommended for any hosted deploy.
- Don't run `git commit --no-verify` (bypasses the hook).

## Deploying

### Streamlit Community Cloud (free, easiest)

1. Sign in at https://share.streamlit.app with GitHub
2. **Create app** → repo `chukovskid/blitz-console` · branch `main` · main file `app/Home.py`
3. **Advanced settings → Secrets:**
   ```toml
   BLITZ_API_KEY = "blitz-..."
   BLITZ_CONSOLE_PASSWORD = "pick-something-strong"
   ```
4. Deploy. URL is auto-assigned, looks like `*.streamlit.app`.

### Fly.io / Render / Railway

`Dockerfile` is included. Set `BLITZ_API_KEY` and `BLITZ_CONSOLE_PASSWORD` as environment variables in the host's secrets UI. For persistent SQLite + run history, mount a volume at `/app` (Fly.io: `fly volumes create blitz_data --size 1`).

## Original CLI (the pipeline this UI wraps)

If you'd rather skip the UI and just run searches from the command line:

```bash
BLITZ_API_KEY=... python3 blitz_pipeline.py search \
  --out leads_raw.json --target 700 --pages-per-tier 3 \
  --per-company 2 --max-credits 1200

BLITZ_API_KEY=... python3 blitz_pipeline.py enrich \
  --in leads_raw.json --out leads_enriched.json --max-credits 2800

python3 blitz_pipeline.py csv --in leads_enriched.json \
  --out leads_for_saleshandy.csv --email-only
```

Both `search` and `enrich` are **resumable** — persist incrementally and skip already-completed work, so a kill mid-run loses only the in-flight call.

## License

MIT — see `LICENSE` if present, or treat as MIT.

## Acknowledgements

- [Blitz API](https://blitz-api.ai) — the underlying B2B data infrastructure
- [Streamlit](https://streamlit.io) — the UI framework
- Apollo and Clay for setting the prospecting-UI design vocabulary this clones
