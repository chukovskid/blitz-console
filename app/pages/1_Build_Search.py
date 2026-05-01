"""Build Search — VSCode-style filter rail."""

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
from app.lib import db, design  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import (  # noqa: E402
    BlitzError, count_people, get_key_info, preview_people,
)
from app.lib.filter_model import (  # noqa: E402
    RunOptions, SearchFilters, filter_summary,
)
from app.lib.runner import spawn_pipeline_run  # noqa: E402

st.set_page_config(page_title="Build Search · Blitz", page_icon="◐",
                   layout="wide")
design.apply()
require_auth()

with st.sidebar:
    design.sidebar_brand()


# ---- session state ----
if "filters" not in st.session_state:
    st.session_state.filters = SearchFilters()
if "options" not in st.session_state:
    st.session_state.options = RunOptions()
if "count_mode" not in st.session_state:
    st.session_state.count_mode = "On click"
if "active_filter" not in st.session_state:
    st.session_state.active_filter = None
if "last_count_at" not in st.session_state:
    st.session_state.last_count_at = None
if "preview_results" not in st.session_state:
    st.session_state.preview_results = None

filters: SearchFilters = st.session_state.filters
options: RunOptions = st.session_state.options


# ---- header ----
design.page_header(
    title="Build search",
    subtitle="Pick filters from the rail. Preview the count, then run.",
    eyebrow="Prospecting",
)


# ---- Quick presets row at top ----
preset_cols = st.columns(len(filter_panel.PRESETS) + 1)
for i, (name, builder) in enumerate(filter_panel.PRESETS.items()):
    if preset_cols[i].button(name, key=f"preset_{i}",
                             use_container_width=True):
        st.session_state.filters = builder()
        st.session_state.active_filter = None
        st.rerun()
preset_cols[-1].markdown(
    f'<p style="color:{design.TEXT_3};font-size:11.5px;margin-top:8px;'
    f'text-align:right;">Quick presets</p>',
    unsafe_allow_html=True,
)

st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)


# ---- 3-column main layout ----
rail_col, panel_col, action_col = st.columns([0.5, 2, 3], gap="medium")


# ============== ICON RAIL ==============
with rail_col:
    filter_panel.render_rail(filters)


# ============== ACTIVE FILTER PANEL ==============
with panel_col:
    filter_panel.render_active_section(filters)


# ============== STATUS + ACTIONS ==============
with action_col:
    body = filters.to_search_body()
    filter_hash = hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()

    # Plain-English summary
    summary = filter_summary(filters)
    if summary:
        design.summary_box(summary)
    else:
        design.empty_state(
            "<b>Pick a preset</b> above, or click an icon on the rail "
            "to start building your filters."
        )

    # Count fetch
    def _get_count(force: bool = False) -> tuple[int | None, str]:
        if not body:
            return None, "none"
        if not force:
            cached = db.get_cached_count(filter_hash)
            if cached is not None:
                return cached, "cache"
        try:
            with st.spinner("Counting…"):
                resp = count_people(body)
            total = int(resp.get("total_results", 0))
            db.cache_count(filter_hash, total)
            st.session_state.last_count_at = time.time()
            try:
                info = get_key_info()
                db.log_balance(info["remaining_credits"], note="count refresh")
            except Exception:
                pass
            return total, "api"
        except BlitzError as e:
            return None, f"error:{e}"

    total, source = (None, "none")
    if body:
        if st.session_state.count_mode == "Auto":
            total, source = _get_count(force=False)
        else:
            cached = db.get_cached_count(filter_hash)
            if cached is not None:
                total, source = cached, "cache"

    # Cost
    target = options.target_leads
    capped = min(total, target) if total is not None else 0
    enrich_cr = capped if options.enrich_emails else 0
    total_cr = capped + enrich_cr
    expected_emails = int(capped * 0.58) if options.enrich_emails else 0

    balance = None
    try:
        balance = get_key_info().get("remaining_credits")
    except Exception:
        pass

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Matches", f"{total:,}" if total is not None else "—")
    with m2:
        st.metric("Est. credits", f"~{total_cr:,}"
                  if total is not None else "—")
    with m3:
        st.metric("Balance", f"{balance:,}" if balance is not None else "—")

    rr1, rr2, rr3 = st.columns([1.4, 1, 1])
    with rr1:
        if total is not None and options.enrich_emails:
            st.caption(f"≈ {expected_emails:,} verified emails (58% rate)")
        elif source.startswith("error"):
            st.error(source.replace("error:", "")[:160])
        elif st.session_state.last_count_at:
            ago = int(time.time() - st.session_state.last_count_at)
            st.caption(f"Last refreshed {ago}s ago")
    with rr2:
        st.session_state.count_mode = st.radio(
            "Mode", ["On click", "Auto"], horizontal=True,
            index=0 if st.session_state.count_mode == "On click" else 1,
            label_visibility="collapsed", key="count_mode_radio",
        )
    with rr3:
        if st.button("Refresh", use_container_width=True,
                     disabled=not body, help="Costs 1 credit"):
            _get_count(force=True)
            st.rerun()

    # Active filter chips
    st.markdown(
        '<p class="bc-eyebrow" style="margin:1.4rem 0 6px;">Active filters</p>',
        unsafe_allow_html=True,
    )
    filter_panel.render_active_chips(filters)

    # Run options
    st.markdown(
        '<p class="bc-eyebrow" style="margin:1.4rem 0 6px;">Run options</p>',
        unsafe_allow_html=True,
    )
    o1, o2, o3 = st.columns(3)
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
        options.hard_credit_cap = st.number_input(
            "Credit cap", min_value=10, max_value=100_000,
            value=options.hard_credit_cap, step=100,
        )
    options.enrich_emails = st.checkbox(
        "Enrich emails (1 credit per attempt, ~58% hit rate)",
        value=options.enrich_emails,
    )

    # ICP profile
    saved = db.list_icps()
    sa, sb = st.columns(2)
    with sa:
        icp_name = st.text_input(
            "ICP name", placeholder="e.g. saas-founders-us",
            label_visibility="collapsed",
        )
    with sb:
        options_list = ["Load saved profile…"] + [i["name"] for i in saved]
        chosen = st.selectbox("Load", options_list,
                              label_visibility="collapsed")

    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("Save profile", use_container_width=True,
                     disabled=not icp_name.strip()):
            db.upsert_icp(icp_name.strip(), filters.to_dict(),
                          options.to_dict())
            st.success(f"Saved '{icp_name.strip()}'")
            st.rerun()
    with sb2:
        if (chosen != "Load saved profile…"
                and st.button("Load profile", use_container_width=True)):
            rec = db.get_icp(chosen)
            if rec:
                st.session_state.filters = SearchFilters.from_dict(
                    json.loads(rec["filters_json"])
                )
                st.session_state.options = RunOptions.from_dict(
                    json.loads(rec["options_json"])
                )
                st.rerun()

    # Run + Preview
    st.markdown('<div style="height:0.6rem"></div>', unsafe_allow_html=True)
    run_col, prev_col = st.columns([2, 1])
    with run_col:
        if st.button("Run search", type="primary",
                     use_container_width=True, disabled=not body):
            if not os.environ.get("BLITZ_API_KEY"):
                st.error("No BLITZ_API_KEY in env. Add it via Settings.")
            else:
                icp_rec = None
                if icp_name.strip():
                    db.upsert_icp(icp_name.strip(), filters.to_dict(),
                                  options.to_dict())
                    icp_rec = db.get_icp(icp_name.strip())
                run_id = db.create_run(
                    icp_id=icp_rec["id"] if icp_rec else None,
                    icp_name=icp_name.strip() or
                             (chosen if chosen != "Load saved profile…" else None),
                    filters_dict=filters.to_dict(),
                    options_dict=options.to_dict(),
                    raw_path="", enriched_path="", csv_path="", log_path="",
                )
                spawn_pipeline_run(run_id, filters, options,
                                   os.environ["BLITZ_API_KEY"])
                st.success(f"Run #{run_id} started. Watch it on **Run history**.")
    with prev_col:
        if st.button("Preview 5 (5 cr)", use_container_width=True,
                     disabled=not body,
                     help="Sample 5 matching profiles to sanity-check the ICP."):
            try:
                with st.spinner("Loading 5 matches…"):
                    resp = preview_people(body, n=5)
                st.session_state.preview_results = resp.get("results") or []
            except BlitzError as e:
                st.error(str(e))

    if st.session_state.preview_results:
        st.markdown(
            '<p class="bc-eyebrow" style="margin:1.4rem 0 6px;">Sample (5)</p>',
            unsafe_allow_html=True,
        )
        for p in st.session_state.preview_results:
            name = p.get("full_name") or "—"
            headline = p.get("headline") or ""
            exps = p.get("experiences") or []
            company = (exps[0] or {}).get("company_name", "") if exps else ""
            country = (p.get("location") or {}).get("country_code", "")
            st.markdown(
                f'<div class="bc-sample">'
                f'<div class="bc-sample-name">{name}</div>'
                f'<div class="bc-sample-meta">{headline[:80]}'
                f'{" · " + company if company else ""}'
                f'{" · " + country if country else ""}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if st.toggle("Show request JSON", value=False):
        st.markdown(
            f'<p class="bc-eyebrow" style="margin-top:1rem;">'
            f'POST /v2/search/people · hash {filter_hash[:10]}</p>',
            unsafe_allow_html=True,
        )
        st.code(json.dumps(body, indent=2), language="json")
