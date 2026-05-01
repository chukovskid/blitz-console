"""Single-shot Blitz endpoint utilities: employee finder, reverse lookup."""

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

from app.lib import reference_data as rd  # noqa: E402
from app.lib.auth import require_auth  # noqa: E402
from app.lib.blitz_client import (  # noqa: E402
    BlitzError,
    employee_finder,
    enrich_company,
    enrich_email,
    enrich_phone,
    reverse_email,
)

st.set_page_config(page_title="Lookup · Blitz", layout="wide")
require_auth()
st.title("🔍 Lookup tools")
st.caption("Single-shot calls to specific Blitz endpoints. Each costs credits — see button labels.")

tabs = st.tabs([
    "Employee Finder",
    "Reverse Email",
    "Email Enrich",
    "Phone Enrich",
    "Company Enrich",
])

# --- Employee Finder ---
with tabs[0]:
    st.subheader("Employees at one company")
    url = st.text_input("Company LinkedIn URL", placeholder="https://www.linkedin.com/company/...")
    cols = st.columns(3)
    with cols[0]:
        levels = st.multiselect("Level", rd.job_levels(), key="ef_levels")
    with cols[1]:
        funcs = st.multiselect("Function", rd.job_functions(), key="ef_funcs")
    with cols[2]:
        countries = st.multiselect(
            "Country",
            options=[c["code"] for c in rd.countries()],
            format_func=lambda code: f"{code} — " + next((c['name'] for c in rd.countries() if c['code'] == code), code),
            key="ef_countries",
        )
    max_n = st.slider("Max results", 1, 50, 10, key="ef_max")
    if st.button("Run employee finder", disabled=not url):
        try:
            resp = employee_finder(
                url,
                country_code=countries or None,
                job_level=levels or None,
                job_function=funcs or None,
                max_results=max_n,
            )
            results = resp.get("results") or []
            st.success(f"Got {len(results)} results.")
            for p in results:
                st.write(f"**{p.get('full_name', '?')}** — {p.get('headline','')}")
                st.caption(p.get("linkedin_url", ""))
        except BlitzError as e:
            st.error(str(e))

# --- Reverse Email ---
with tabs[1]:
    st.subheader("Email → person profile")
    email = st.text_input("Email", placeholder="someone@company.com", key="rev_email")
    if st.button("Lookup", disabled=not email):
        try:
            resp = reverse_email(email.strip())
            st.json(resp)
        except BlitzError as e:
            st.error(str(e))

# --- Email Enrich ---
with tabs[2]:
    st.subheader("LinkedIn URL → verified email")
    url = st.text_input("Person LinkedIn URL", key="ee_url")
    if st.button("Find email", disabled=not url):
        try:
            resp = enrich_email(url.strip())
            st.json(resp)
        except BlitzError as e:
            st.error(str(e))

# --- Phone Enrich ---
with tabs[3]:
    st.subheader("LinkedIn URL → phone")
    url = st.text_input("Person LinkedIn URL", key="ph_url")
    if st.button("Find phone", disabled=not url):
        try:
            resp = enrich_phone(url.strip())
            st.json(resp)
        except BlitzError as e:
            st.error(str(e))

# --- Company Enrich ---
with tabs[4]:
    st.subheader("Company LinkedIn URL → full profile")
    url = st.text_input("Company LinkedIn URL", key="ce_url")
    if st.button("Enrich company", disabled=not url):
        try:
            resp = enrich_company(url.strip())
            st.json(resp)
        except BlitzError as e:
            st.error(str(e))
