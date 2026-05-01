# Onboarding plan — Blitz Console

> Hey 👋 I built a small console on top of the [Blitz API](https://blitz-api.ai) for B2B prospecting. Apollo-style filters, live result counts, exports SalesHandy-ready CSVs. Source: https://github.com/chukovskid/blitz-console
>
> This doc tells you how to start using it in <10 minutes — pick the path that fits.

---

## TL;DR

| You want to… | Do this |
|---|---|
| Just try the UI, no setup | Open the **hosted URL** I sent you separately + paste the password I sent. Done. |
| Run real searches with credits | **Run locally** — clone, set your own API key, launch. ~5 min setup. |
| Hand it to your AI agent | Forward the **"For your AI agent"** section below. It's self-contained. |

---

## Path A · Use the hosted version (zero setup)

1. Open the URL I sent (looks like `https://blitz-console-XXXXXX.streamlit.app`)
2. Lock screen → paste the password I sent in DM
3. Go to **Build Search** in the left sidebar
4. Add a filter (e.g. Industry → "Software Development", employees 20–100)
5. Click **🔄 Refresh count** → see how many people match (costs 1 credit per refresh)
6. Don't click **▶ Run search now** without telling me — that spends real credits to pull leads (a 1,000-lead run with email enrichment uses ~1,700 credits)

> **Important about the hosted version:** State doesn't persist across redeploys (Streamlit Cloud free tier has no disk persistence). Saved ICPs and run history will reset when I push updates. For real outreach work, **run locally instead.**

---

## Path B · Run locally (recommended for real searches)

### Prereqs
- Python 3.10+ (`python3 --version`)
- Git
- Your own Blitz API key — get one at https://blitz-api.ai. Free trial includes ~10k credits.

### Setup

```bash
git clone https://github.com/chukovskid/blitz-console.git
cd blitz-console

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

bash scripts/install-hooks.sh

cp .env.example .env
```

Now open `.env` and replace the placeholder with your real Blitz key. Then:

```bash
.venv/bin/streamlit run app/Home.py
```

Opens at http://localhost:8501. The Home page should show your credit balance.

### Smoke test (costs 1 credit)

1. Go to **Build Search**
2. Sidebar → 🏢 Company → Industry → add `Software Development`
3. Sidebar → Company size → set 20–100
4. Top of page → click **🔄 Refresh count**
5. Should show ~1,694 matches and decrement your balance by 1

If you see a number, the integration works. From here you can either save the filters as an ICP and click Run, or use the lookup tools directly.

---

## What the app actually does

The UI has 6 pages on the sidebar:

- **🏠 Home** — credit balance, recent runs, saved ICPs at a glance
- **🎯 Build Search** — Apollo-style filter panel; the main thing you'll use
- **📚 Saved ICPs** — manage filter presets
- **📜 Run History** — live progress for in-flight runs, CSV downloads when done
- **🔍 Lookup Tools** — single-shot endpoints (employee finder, reverse email, etc.)
- **⚙️ Settings** — API key + credit-history chart

### Filters available

**Company:** industry · size · founded year · HQ country/city/continent/sales region · description keywords · company type · min followers · name · LinkedIn URL.

**People:** job title · seniority (C-Team / VP / Director / Manager / Staff / Other) · department/function · location country/city/continent/sales region · min connections.

**Not available** (Blitz doesn't expose these, so the UI doesn't fake them): revenue · funding · technographics · job postings · state-level geo · years experience · past companies · education / skills.

### Cost reference

| Action | Cost |
|---|---|
| Refresh the live count | **1 credit** (1 search call with `max_results: 1`) |
| Search for 100 leads | **~100 credits** (1 cr per result) |
| Enrich 100 emails | **~100 credits** (1 cr per attempt, ~58% hit rate) |
| Look up one email's owner | 1 credit |
| Single company employee finder, 10 results | 10 credits |

Email-only outreach run targeting 1,000 verified contacts ≈ **1,700 credits**.

---

## Common gotchas

- **Industry strings are case-sensitive.** Use the picker, don't free-type. `software development` (lowercase) returns zero results.
- **No state-level geography.** Blitz only has country + city. If you want "California-only", filter by city `San Francisco` etc., or by country `US` and post-filter the CSV.
- **`[brackets]` in job titles toggle exact-match.** `[Founder]` matches only people whose title is exactly "Founder". `Founder` (no brackets) is keyword match (also catches "Co-Founder", "Founder & CEO", etc.).
- **The pipeline is resumable.** If you kill a run mid-way, just click Run again with the same filters — it picks up from the last persisted page.

---

## For your AI agent (Claude / Cursor / Copilot)

If you're handing this to an agent to set up, paste this entire block:

> **Task:** Set up the Blitz Console app locally on this machine and verify it runs.
>
> Source: https://github.com/chukovskid/blitz-console (public repo; clone normally)
>
> **Steps:**
>
> 1. `git clone https://github.com/chukovskid/blitz-console.git && cd blitz-console`
> 2. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
> 3. `bash scripts/install-hooks.sh` (installs pre-commit hook that blocks API key leaks)
> 4. **Ask the user for their Blitz API key.** Do not invent one. Format: `blitz-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`.
> 5. `cp .env.example .env`, then edit `.env` to replace the placeholder with the real key. Verify with `git check-ignore .env` (must print `.env`).
> 6. `.venv/bin/streamlit run app/Home.py` — should open at http://localhost:8501
> 7. Verify the Home page shows a numeric credit balance (not an error). If it shows "No API key set", the `.env` didn't load — check syntax (no quotes around the value, no whitespace).
> 8. Smoke test (only with user permission, costs 1 credit): on Build Search, add Industry "Software Development", set employees 20–100, click "🔄 Refresh count". Should return a number and decrement balance by 1.
>
> **Architecture cheat sheet:**
> - `app/Home.py` is the entry point
> - `app/pages/` are the sidebar pages
> - `app/components/filter_panel.py` is the 14-filter UI
> - `app/lib/blitz_client.py` is the API wrapper
> - `app/lib/filter_model.py` is the `SearchFilters` dataclass with `to_search_body()` → `to_dict()` ↔ JSON ↔ widget state
> - `app/lib/db.py` is SQLite (`blitz.db`, gitignored — survives between sessions, lost on hosted-cloud restarts)
> - `blitz_pipeline.py` is the search/enrich/csv pipeline that runs as a subprocess, resumable, persists per page
>
> **Things the agent should know:**
> - **Cost model is empirical.** `/v2/search/people` charges 1 credit per result returned. `/v2/enrichment/email` charges 1 credit per attempt regardless of hit/miss (Blitz docs incorrectly say "per found"). Email hit rate observed at ~58% on Software/IT 20–100 employee companies.
> - **Industry strings are case-sensitive** and must match Blitz's 534-value canonical list (already in `app/data/industries.json`).
> - **No state-level geography.** Don't try to add a state filter — the API rejects it.
> - **Optional password gate:** set `BLITZ_CONSOLE_PASSWORD` env var to require a password on every page.
> - **Pre-commit hook:** blocks committing real API keys, `.env`, `blitz.db`, `.claude/settings.local.json`. Don't run `git commit --no-verify`.
>
> **Done = ** the user sees their credit balance on the Home page and a number after clicking "Refresh count" on Build Search. Report the URL and current balance.

---

## When you hit weird stuff

- **"BLITZ_API_KEY env var not set" error:** the `.env` file isn't being loaded. Check it's in the project root (same dir as `app/`) and has the form `BLITZ_API_KEY=blitz-...` with no quotes and no leading whitespace.
- **Credit balance keeps drifting downward when you're not running anything:** likely the API key is leaked somewhere else. Rotate the key in the Blitz dashboard.
- **Streamlit "module not found" errors:** you launched system Python instead of the venv. Use `.venv/bin/streamlit run app/Home.py` explicitly, not just `streamlit run …`.
- **Run shows "process exited" without producing CSV:** check `runs/run_NNNNNN/run.log` for the actual error. Usually a malformed filter (e.g. invalid industry string) or out of credits.
- **Anything else weird:** ping me. The codebase is small (~2700 LOC) and well-commented; if you read `app/Home.py` and `app/pages/1_Build_Search.py` you'll have most of it.

Have fun. Don't burn all my credits 🙂
