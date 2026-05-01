"""The Apollo-style filter panel.

Reads/writes a SearchFilters dataclass via st.session_state. Every widget is
keyed so values survive Streamlit reruns. Renders into the sidebar by
default — caller can pass a different container.
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from app.lib import reference_data as rd
from app.lib.filter_model import (
    EMPLOYEE_RANGE_BUCKETS,
    SearchFilters,
)


def _multi_chip_input(label: str, key: str, current: list[str]) -> list[str]:
    """Lightweight chip input: textarea, one entry per line. Order preserved.

    A more polished chip widget would use streamlit-tags; for v1 we keep deps
    minimal.
    """
    raw = st.text_area(
        label,
        value="\n".join(current),
        key=key,
        height=68,
        help="One value per line. Wrap in [brackets] for exact match.",
    )
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _include_exclude_chip_block(
    label: str, prefix: str, ie, help_text: str | None = None
):
    if help_text:
        st.caption(help_text)
    inc = _multi_chip_input(f"{label} — include", f"{prefix}_inc", ie.include)
    exc = _multi_chip_input(f"{label} — exclude", f"{prefix}_exc", ie.exclude)
    ie.include = inc
    ie.exclude = exc


def render(filters: SearchFilters, container=None) -> SearchFilters:
    """Render filter widgets, mutate `filters` in place, return it."""
    c = container or st.sidebar

    with c:
        st.markdown("### Filters")

        # ============== COMPANY ==============
        with st.expander("🏢 Company", expanded=True):
            # Industry
            st.markdown("**Industry**")
            filters.company.industry.include = st.multiselect(
                "Include industries",
                options=rd.industries(),
                default=filters.company.industry.include,
                key="ind_inc",
                placeholder="Pick from 534 LinkedIn industries",
            )
            filters.company.industry.exclude = st.multiselect(
                "Exclude industries",
                options=rd.industries(),
                default=filters.company.industry.exclude,
                key="ind_exc",
            )

            # Employee size — radio bucket vs numeric
            st.markdown("**Company size**")
            size_mode = st.radio(
                "Size mode",
                ["Numeric range", "Buckets"],
                key="size_mode",
                horizontal=True,
                label_visibility="collapsed",
            )
            if size_mode == "Numeric range":
                col1, col2 = st.columns(2)
                with col1:
                    min_v = st.number_input(
                        "Min",
                        min_value=0,
                        max_value=1_000_000,
                        value=int(filters.company.employee_count_min or 0),
                        step=10,
                        key="emp_min",
                    )
                with col2:
                    max_v = st.number_input(
                        "Max",
                        min_value=0,
                        max_value=1_000_000,
                        value=int(filters.company.employee_count_max or 0),
                        step=10,
                        key="emp_max",
                    )
                filters.company.employee_count_min = min_v if min_v > 0 else None
                filters.company.employee_count_max = max_v if max_v > 0 else None
                filters.company.employee_range = []  # mutually exclusive
            else:
                filters.company.employee_range = st.multiselect(
                    "Buckets",
                    options=EMPLOYEE_RANGE_BUCKETS,
                    default=filters.company.employee_range,
                    key="emp_buckets",
                )
                filters.company.employee_count_min = None
                filters.company.employee_count_max = None

            # Founded year
            st.markdown("**Founded year**")
            col1, col2 = st.columns(2)
            with col1:
                fmin = st.number_input(
                    "Min year",
                    min_value=0,
                    max_value=2100,
                    value=int(filters.company.founded_year_min or 0),
                    step=1,
                    key="fy_min",
                )
            with col2:
                fmax = st.number_input(
                    "Max year",
                    min_value=0,
                    max_value=2100,
                    value=int(filters.company.founded_year_max or 0),
                    step=1,
                    key="fy_max",
                )
            filters.company.founded_year_min = fmin if fmin > 0 else None
            filters.company.founded_year_max = fmax if fmax > 0 else None

            # HQ location
            st.markdown("**HQ location**")
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            filters.company.hq_country_code = st.multiselect(
                "Country (HQ)",
                options=country_options,
                default=filters.company.hq_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="hq_country",
            )
            filters.company.hq_continent = st.multiselect(
                "Continent (HQ)",
                options=rd.continents(),
                default=filters.company.hq_continent,
                key="hq_cont",
            )
            filters.company.hq_sales_region = st.multiselect(
                "Sales region (HQ)",
                options=rd.sales_regions(),
                default=filters.company.hq_sales_region,
                key="hq_sr",
            )
            _include_exclude_chip_block(
                "HQ city", "hq_city", filters.company.hq_city,
                help_text="Cities filter only — Blitz has no state/region level.",
            )

            # Description keywords
            st.markdown("**Description keywords**")
            _include_exclude_chip_block(
                "Description keywords", "desc_kw", filters.company.keywords
            )

            # Company type
            st.markdown("**Company type**")
            filters.company.type_.include = st.multiselect(
                "Include types",
                options=rd.company_types(),
                default=filters.company.type_.include,
                key="ctype_inc",
            )
            filters.company.type_.exclude = st.multiselect(
                "Exclude types",
                options=rd.company_types(),
                default=filters.company.type_.exclude,
                key="ctype_exc",
            )

            # Min followers
            mlf = st.number_input(
                "Min LinkedIn followers",
                min_value=0,
                max_value=10_000_000,
                value=int(filters.company.min_linkedin_followers or 0),
                step=100,
                key="min_followers",
            )
            filters.company.min_linkedin_followers = mlf if mlf > 0 else None

            # Company name
            st.markdown("**Company name**")
            _include_exclude_chip_block(
                "Company name", "cname", filters.company.name,
                help_text="Keyword by default. Wrap a name in [brackets] for exact match.",
            )

        # ============== PEOPLE ==============
        with st.expander("👤 People", expanded=True):
            st.markdown("**Job title**")
            _include_exclude_chip_block(
                "Job title", "title", filters.people.job_title,
                help_text="Keyword default. Use [Founder] for exact title match.",
            )
            filters.people.job_title_search_headline = st.checkbox(
                "Also search LinkedIn headline for these titles",
                value=filters.people.job_title_search_headline,
                key="title_headline",
            )

            st.markdown("**Seniority**")
            filters.people.job_level = st.multiselect(
                "Job level",
                options=rd.job_levels(),
                default=filters.people.job_level,
                key="job_level",
                help="C-Team is highest; Other catches founders/owners.",
            )

            st.markdown("**Department / function**")
            filters.people.job_function = st.multiselect(
                "Job function",
                options=rd.job_functions(),
                default=filters.people.job_function,
                key="job_function",
            )

            st.markdown("**Person location**")
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            filters.people.location_country_code = st.multiselect(
                "Country (person)",
                options=country_options,
                default=filters.people.location_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="ploc_country",
            )
            filters.people.location_continent = st.multiselect(
                "Continent (person)",
                options=rd.continents(),
                default=filters.people.location_continent,
                key="ploc_cont",
            )
            filters.people.location_sales_region = st.multiselect(
                "Sales region (person)",
                options=rd.sales_regions(),
                default=filters.people.location_sales_region,
                key="ploc_sr",
            )
            city_raw = st.text_area(
                "City (person)",
                value="\n".join(filters.people.location_city),
                key="ploc_city",
                height=68,
                help="One per line. Country and city only — no state filter.",
            )
            filters.people.location_city = [
                line.strip() for line in city_raw.splitlines() if line.strip()
            ]

            mc = st.number_input(
                "Min LinkedIn connections",
                min_value=0,
                max_value=500,
                value=int(filters.people.min_connections or 0),
                step=10,
                key="min_conn",
            )
            filters.people.min_connections = mc if mc > 0 else None

    return filters
