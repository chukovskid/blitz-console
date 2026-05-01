"""The Apollo-style filter screen — the core of the app.

Layout:
- Left sidebar: filter panel (every supported Blitz filter)
- Main area: live count + cost estimator + ICP save/load + Run controls
- JSON drawer: shows the actual API request body for power users
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Load .env
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import streamlit as st  # noqa: E402

from app.components import filter_panel  # noqa: E402
from app.lib import db  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import BlitzError, count_people, get_key_info  # noqa: E402
from app.lib.filter_model import RunOptions, SearchFilters  # noqa: E402
from app.lib.runner import spawn_pipeline_run  # noqa: E402

st.set_page_config(page_title="Build Search · Blitz", layout="wide")
require_auth()

# ---- session state init ----
if "filters" not in st.session_state:
    st.session_state.filters = SearchFilters()
if "options" not in st.session_state:
    st.session_state.options = RunOptions()
if "count_mode" not in st.session_state:
    st.session_state.count_mode = "On click"  # safer default; user can flip

filters: SearchFilters = st.session_state.filters
options: RunOptions = st.session_state.options


# ---- sidebar: filter panel ----
filter_panel.render(filters)


# ---- main area ----
st.title("🎯 Build Search")

body = filters.to_search_body()
filter_hash = hashlib.sha1(
    json.dumps(body, sort_keys=True).encode()
).hexdigest()


def _get_count(force_refresh: bool = False) -> tuple[int | None, str]:
    """Returns (total_results, source). source ∈ {'cache','api','none','error:...'}"""
    if not body:
        return None, "none"
    if not force_refresh:
        cached = db.get_cached_count(filter_hash)
        if cached is not None:
            return cached, "cache"
    try:
        resp = count_people(body)
        total = int(resp.get("total_results", 0))
        db.cache_count(filter_hash, total)
        # Best-effort balance update
        try:
            info = get_key_info()
            db.log_balance(info["remaining_credits"], note="count refresh")
        except Exception:
            pass
        return total, "api"
    except BlitzError as e:
        return None, f"error:{e}"


# Top metric row
c1, c2, c3, c4 = st.columns([1.4, 1, 1, 2])

count_mode = c4.radio(
    "Count mode",
    ["On click", "Auto (1 cr per change)"],
    horizontal=True,
    index=["On click", "Auto (1 cr per change)"].index(st.session_state.count_mode),
    key="count_mode_radio",
    help="Auto fires a 1-credit count call whenever filters change. On click = manual.",
)
st.session_state.count_mode = count_mode

# Decide whether to call API.
total = None
source = "none"
if not body:
    c1.metric("Matches", "—", help="Add a filter to enable count")
elif count_mode.startswith("Auto"):
    total, source = _get_count(force_refresh=False)
    c1.metric("Matches", f"{total:,}" if total is not None else "?")
else:
    cached = db.get_cached_count(filter_hash)
    if cached is not None:
        total = cached
        source = "cache"
    c1.metric("Matches", f"{total:,}" if total is not None else "—")

if c2.button("🔄 Refresh count", help="Costs 1 credit", disabled=not body):
    total, source = _get_count(force_refresh=True)
    st.rerun()

# Cost estimate
if total is not None:
    target = options.target_leads
    per_co = options.per_company_cap
    capped = min(total, target)
    search_cr = capped
    enrich_cr = capped if options.enrich_emails else 0
    total_cr = search_cr + enrich_cr
    expected_emails = int(capped * 0.58) if options.enrich_emails else 0
    c3.metric("Est. credits", f"~{total_cr:,}")
    st.caption(
        f"Search ~{search_cr:,} cr + email enrichment ~{enrich_cr:,} cr · "
        f"~{expected_emails} verified emails at observed 58% hit rate. "
        f"Source: {source}."
    )
elif source.startswith("error"):
    c3.error(source.replace("error:", ""))


st.divider()

# ---- Run options ----
st.subheader("Run options")
o1, o2, o3, o4 = st.columns(4)
with o1:
    options.target_leads = st.number_input(
        "Target leads", min_value=10, max_value=50_000,
        value=options.target_leads, step=50,
    )
with o2:
    options.per_company_cap = st.number_input(
        "Per-company cap", min_value=1, max_value=20,
        value=options.per_company_cap, step=1,
    )
with o3:
    options.enrich_emails = st.checkbox("Enrich emails", value=options.enrich_emails)
with o4:
    options.hard_credit_cap = st.number_input(
        "Hard credit cap", min_value=10, max_value=100_000,
        value=options.hard_credit_cap, step=100,
        help="Pipeline stops enrichment when this many credits have been spent.",
    )


# ---- ICP save / load ----
st.subheader("ICP profile")
saved = db.list_icps()
sa, sb, sc = st.columns([2, 2, 1])

with sa:
    icp_name = st.text_input("Save as", placeholder="e.g. saas-founders-us")
    if st.button("💾 Save ICP", disabled=not icp_name.strip()):
        db.upsert_icp(icp_name.strip(), filters.to_dict(), options.to_dict())
        st.success(f"Saved '{icp_name.strip()}'")
        st.rerun()

with sb:
    options_list = ["—"] + [i["name"] for i in saved]
    chosen = st.selectbox("Load saved", options_list)
    if chosen != "—" and st.button("Load"):
        rec = db.get_icp(chosen)
        if rec:
            st.session_state.filters = SearchFilters.from_dict(json.loads(rec["filters_json"]))
            st.session_state.options = RunOptions.from_dict(json.loads(rec["options_json"]))
            st.rerun()

with sc:
    if st.button("↺ Reset all"):
        st.session_state.filters = SearchFilters()
        st.session_state.options = RunOptions()
        st.rerun()


# ---- Action buttons ----
st.divider()
ac1, ac2, ac3 = st.columns([1, 1, 1])

with ac1:
    if st.button("▶ Run search now", type="primary", disabled=not body):
        # Create run row + spawn driver subprocess.
        if not os.environ.get("BLITZ_API_KEY"):
            st.error("No BLITZ_API_KEY in env. Add it to .env and restart.")
        else:
            icp_rec = None
            if icp_name.strip():
                db.upsert_icp(icp_name.strip(), filters.to_dict(), options.to_dict())
                icp_rec = db.get_icp(icp_name.strip())
            run_id = db.create_run(
                icp_id=icp_rec["id"] if icp_rec else None,
                icp_name=icp_name.strip() or chosen if chosen != "—" else None,
                filters_dict=filters.to_dict(),
                options_dict=options.to_dict(),
                raw_path="",
                enriched_path="",
                csv_path="",
                log_path="",
            )
            spawn_pipeline_run(run_id, filters, options, os.environ["BLITZ_API_KEY"])
            st.success(f"Started run #{run_id}. Watch it on the Run History page.")
            st.session_state["last_run_id"] = run_id

with ac2:
    show_json = st.checkbox("📋 Show request JSON")

with ac3:
    st.caption(f"Filter hash: `{filter_hash[:10]}`")


if show_json:
    st.code(json.dumps(body, indent=2), language="json")


# ---- Footer notes ----
st.divider()
st.caption(
    "Filters only show fields Blitz's API actually supports. "
    "Apollo features Blitz doesn't expose (revenue, funding, technographics, "
    "state-level geo, years of experience) are deliberately omitted — they "
    "would silently no-op."
)
