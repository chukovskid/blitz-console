"""Single-shot Blitz endpoint utilities."""

from __future__ import annotations

import json
import os
import sys
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

from app.lib import design, reference_data as rd  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import (  # noqa: E402
    BlitzError,
    employee_finder,
    enrich_company,
    enrich_email,
    enrich_phone,
    reverse_email,
)

st.set_page_config(page_title="Lookup · Blitz", page_icon="◐", layout="wide")
design.apply()
design.topnav(current="Lookup_Tools")
require_auth()

design.page_header(
    title="Lookup tools",
    subtitle="Single-shot calls. Each costs credits — see the button label.",
    eyebrow="Utilities",
)

tabs = st.tabs([
    "Employee finder",
    "Reverse email",
    "Email enrich",
    "Phone enrich",
    "Company enrich",
])


# --- Employee Finder ---
with tabs[0]:
    st.markdown("### Employees at one company")
    st.caption("Returns up to 50 people from a single LinkedIn company URL.")
    url = st.text_input(
        "Company LinkedIn URL",
        placeholder="https://www.linkedin.com/company/…",
        key="ef_url",
    )
    cols = st.columns(3)
    with cols[0]:
        levels = st.multiselect("Level", rd.job_levels(), key="ef_levels")
    with cols[1]:
        funcs = st.multiselect("Function", rd.job_functions(), key="ef_funcs")
    with cols[2]:
        country_options = [c["code"] for c in rd.countries()]
        countries = st.multiselect(
            "Country",
            options=country_options,
            format_func=lambda code: f"{code} — " + next(
                (c["name"] for c in rd.countries() if c["code"] == code), code
            ),
            key="ef_countries",
        )
    max_n = st.slider("Max results", 1, 50, 10, key="ef_max")
    if st.button("Run · 1 cr per result", disabled=not url, type="primary"):
        try:
            resp = employee_finder(
                url,
                country_code=countries or None,
                job_level=levels or None,
                job_function=funcs or None,
                max_results=max_n,
            )
            results = resp.get("results") or []
            st.success(f"Found {len(results)} results.")
            for p in results:
                st.markdown(
                    f"<div style='padding:10px 0;border-bottom:1px solid {design.BORDER};"
                    f"font-size:13.5px;'>"
                    f"<div style='font-weight:500;'>{p.get('full_name','—')}</div>"
                    f"<div style='color:{design.TEXT_2};font-size:12.5px;margin-top:2px;'>"
                    f"{p.get('headline','')}</div>"
                    f"<div style='color:{design.TEXT_3};font-size:11.5px;margin-top:2px;'>"
                    f"{p.get('linkedin_url','')}</div></div>",
                    unsafe_allow_html=True,
                )
        except BlitzError as e:
            st.error(str(e))


# --- Reverse Email ---
with tabs[1]:
    st.markdown("### Email → person profile")
    email = st.text_input("Email", placeholder="someone@company.com", key="rev_email")
    if st.button("Look up · 1 cr", disabled=not email, key="rev_btn", type="primary"):
        try:
            resp = reverse_email(email.strip())
            st.code(json.dumps(resp, indent=2), language="json")
        except BlitzError as e:
            st.error(str(e))


# --- Email Enrich ---
with tabs[2]:
    st.markdown("### LinkedIn URL → verified email")
    url = st.text_input("Person LinkedIn URL", key="ee_url")
    if st.button("Find email · 1 cr", disabled=not url, key="ee_btn", type="primary"):
        try:
            resp = enrich_email(url.strip())
            st.code(json.dumps(resp, indent=2), language="json")
        except BlitzError as e:
            st.error(str(e))


# --- Phone Enrich ---
with tabs[3]:
    st.markdown("### LinkedIn URL → phone")
    url = st.text_input("Person LinkedIn URL", key="ph_url")
    if st.button("Find phone · 1 cr", disabled=not url, key="ph_btn", type="primary"):
        try:
            resp = enrich_phone(url.strip())
            st.code(json.dumps(resp, indent=2), language="json")
        except BlitzError as e:
            st.error(str(e))


# --- Company Enrich ---
with tabs[4]:
    st.markdown("### Company LinkedIn URL → full profile")
    url = st.text_input("Company LinkedIn URL", key="ce_url")
    if st.button("Enrich company · 1 cr", disabled=not url, key="ce_btn", type="primary"):
        try:
            resp = enrich_company(url.strip())
            st.code(json.dumps(resp, indent=2), language="json")
        except BlitzError as e:
            st.error(str(e))
