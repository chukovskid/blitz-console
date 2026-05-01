"""Apollo-style filter panel.

Renders into the sidebar. Reads/writes a SearchFilters dataclass via
st.session_state. Every widget is keyed so values survive Streamlit reruns.
"""

from __future__ import annotations

import streamlit as st

from app.lib import reference_data as rd
from app.lib.filter_model import EMPLOYEE_RANGE_BUCKETS, SearchFilters


# ----- helpers -------------------------------------------------------------


def _chip_input(label: str, key: str, current: list[str], height: int = 64,
                placeholder: str = "") -> list[str]:
    """Lightweight chip input: textarea, one entry per line."""
    raw = st.text_area(
        label,
        value="\n".join(current),
        key=key,
        height=height,
        placeholder=placeholder,
        label_visibility="collapsed",
    )
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _ie_block(label_inc: str, label_exc: str, prefix: str, ie,
              placeholder: str = "") -> None:
    """Two stacked chip inputs: include then exclude."""
    st.caption(label_inc)
    ie.include = _chip_input("Include", f"{prefix}_inc", ie.include,
                             placeholder=placeholder)
    st.caption(label_exc)
    ie.exclude = _chip_input("Exclude", f"{prefix}_exc", ie.exclude)


def _section(title: str, expanded: bool = False):
    return st.expander(title, expanded=expanded)


# ----- main render ---------------------------------------------------------


def render(filters: SearchFilters, container=None) -> SearchFilters:
    c = container or st.sidebar

    with c:
        st.markdown("### Filters")

        # ============== COMPANY =====================================
        with _section("Company", expanded=True):

            st.caption("Industry — include")
            filters.company.industry.include = st.multiselect(
                "Industry — include",
                options=rd.industries(),
                default=filters.company.industry.include,
                key="ind_inc",
                placeholder="Search 534 industries",
                label_visibility="collapsed",
            )
            st.caption("Industry — exclude")
            filters.company.industry.exclude = st.multiselect(
                "Industry — exclude",
                options=rd.industries(),
                default=filters.company.industry.exclude,
                key="ind_exc",
                label_visibility="collapsed",
            )

            st.caption("Company size")
            size_mode = st.radio(
                "Mode",
                ["Range", "Buckets"],
                key="size_mode",
                horizontal=True,
                label_visibility="collapsed",
            )
            if size_mode == "Range":
                col1, col2 = st.columns(2)
                with col1:
                    min_v = st.number_input(
                        "Min", min_value=0, max_value=1_000_000,
                        value=int(filters.company.employee_count_min or 0),
                        step=10, key="emp_min",
                    )
                with col2:
                    max_v = st.number_input(
                        "Max", min_value=0, max_value=1_000_000,
                        value=int(filters.company.employee_count_max or 0),
                        step=10, key="emp_max",
                    )
                filters.company.employee_count_min = min_v if min_v > 0 else None
                filters.company.employee_count_max = max_v if max_v > 0 else None
                filters.company.employee_range = []
            else:
                filters.company.employee_range = st.multiselect(
                    "Buckets",
                    options=EMPLOYEE_RANGE_BUCKETS,
                    default=filters.company.employee_range,
                    key="emp_buckets",
                    label_visibility="collapsed",
                )
                filters.company.employee_count_min = None
                filters.company.employee_count_max = None

            st.caption("Founded year (range)")
            col1, col2 = st.columns(2)
            with col1:
                fmin = st.number_input(
                    "From", min_value=0, max_value=2100,
                    value=int(filters.company.founded_year_min or 0),
                    step=1, key="fy_min",
                )
            with col2:
                fmax = st.number_input(
                    "To", min_value=0, max_value=2100,
                    value=int(filters.company.founded_year_max or 0),
                    step=1, key="fy_max",
                )
            filters.company.founded_year_min = fmin if fmin > 0 else None
            filters.company.founded_year_max = fmax if fmax > 0 else None

        with _section("HQ location", expanded=False):
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            st.caption("Country")
            filters.company.hq_country_code = st.multiselect(
                "Country",
                options=country_options,
                default=filters.company.hq_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="hq_country",
                label_visibility="collapsed",
            )
            st.caption("Continent")
            filters.company.hq_continent = st.multiselect(
                "Continent",
                options=rd.continents(),
                default=filters.company.hq_continent,
                key="hq_cont",
                label_visibility="collapsed",
            )
            st.caption("Sales region")
            filters.company.hq_sales_region = st.multiselect(
                "Sales region",
                options=rd.sales_regions(),
                default=filters.company.hq_sales_region,
                key="hq_sr",
                label_visibility="collapsed",
            )
            _ie_block(
                "City — include", "City — exclude", "hq_city",
                filters.company.hq_city,
                placeholder="One per line — Blitz has no state filter",
            )

        with _section("Description & type", expanded=False):
            _ie_block(
                "Keywords — include", "Keywords — exclude", "desc_kw",
                filters.company.keywords,
                placeholder="e.g. AI, b2b, fintech",
            )
            st.caption("Type — include")
            filters.company.type_.include = st.multiselect(
                "Type include",
                options=rd.company_types(),
                default=filters.company.type_.include,
                key="ctype_inc",
                label_visibility="collapsed",
            )
            st.caption("Type — exclude")
            filters.company.type_.exclude = st.multiselect(
                "Type exclude",
                options=rd.company_types(),
                default=filters.company.type_.exclude,
                key="ctype_exc",
                label_visibility="collapsed",
            )
            mlf = st.number_input(
                "Min LinkedIn followers",
                min_value=0, max_value=10_000_000,
                value=int(filters.company.min_linkedin_followers or 0),
                step=100, key="min_followers",
            )
            filters.company.min_linkedin_followers = mlf if mlf > 0 else None

        with _section("Company name", expanded=False):
            _ie_block(
                "Name — include", "Name — exclude", "cname",
                filters.company.name,
                placeholder="Keyword by default. [Brackets] = exact match.",
            )

        # ============== PEOPLE ======================================
        with _section("People · title & seniority", expanded=True):
            _ie_block(
                "Job title — include", "Job title — exclude", "title",
                filters.people.job_title,
                placeholder="Keyword default. [Founder] for exact match.",
            )
            filters.people.job_title_search_headline = st.checkbox(
                "Also search headlines",
                value=filters.people.job_title_search_headline,
                key="title_headline",
            )
            st.caption("Seniority")
            filters.people.job_level = st.multiselect(
                "Seniority",
                options=rd.job_levels(),
                default=filters.people.job_level,
                key="job_level",
                label_visibility="collapsed",
            )
            st.caption("Department / function")
            filters.people.job_function = st.multiselect(
                "Function",
                options=rd.job_functions(),
                default=filters.people.job_function,
                key="job_function",
                label_visibility="collapsed",
            )

        with _section("People · location & network", expanded=False):
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            st.caption("Country")
            filters.people.location_country_code = st.multiselect(
                "Person country",
                options=country_options,
                default=filters.people.location_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="ploc_country",
                label_visibility="collapsed",
            )
            st.caption("Continent")
            filters.people.location_continent = st.multiselect(
                "Person continent",
                options=rd.continents(),
                default=filters.people.location_continent,
                key="ploc_cont",
                label_visibility="collapsed",
            )
            st.caption("Sales region")
            filters.people.location_sales_region = st.multiselect(
                "Person sales region",
                options=rd.sales_regions(),
                default=filters.people.location_sales_region,
                key="ploc_sr",
                label_visibility="collapsed",
            )
            st.caption("City")
            city_raw = st.text_area(
                "Person city",
                value="\n".join(filters.people.location_city),
                key="ploc_city",
                height=64,
                placeholder="One per line",
                label_visibility="collapsed",
            )
            filters.people.location_city = [
                line.strip() for line in city_raw.splitlines() if line.strip()
            ]
            mc = st.number_input(
                "Min LinkedIn connections",
                min_value=0, max_value=500,
                value=int(filters.people.min_connections or 0),
                step=10, key="min_conn",
            )
            filters.people.min_connections = mc if mc > 0 else None

    return filters
