"""Compact filter panel for the Build Search page.

Renders into a passed container (typically a left column of the main area).
Designed for clarity and density: every section header shows the count of
active filters; exclude inputs are hidden behind a "More" toggle to keep the
default view clean.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from app.lib import design, reference_data as rd
from app.lib.filter_model import EMPLOYEE_RANGE_BUCKETS, SearchFilters


# ----- helpers -------------------------------------------------------------


def _ie_count(ie) -> int:
    return len(ie.include) + len(ie.exclude)


def _section_count(filters: SearchFilters, section: str) -> int:
    cf = filters.company
    pf = filters.people
    if section == "industry":
        return _ie_count(cf.industry)
    if section == "size":
        n = 1 if cf.employee_range else 0
        if cf.employee_count_min is not None or cf.employee_count_max is not None:
            n += 1
        return n
    if section == "founded":
        return 1 if (cf.founded_year_min or cf.founded_year_max) else 0
    if section == "location_co":
        n = len(cf.hq_country_code) + len(cf.hq_continent) + len(cf.hq_sales_region)
        n += _ie_count(cf.hq_city)
        return n
    if section == "description":
        return _ie_count(cf.keywords) + _ie_count(cf.type_) + (
            1 if cf.min_linkedin_followers else 0
        )
    if section == "company_name":
        return _ie_count(cf.name)
    if section == "title":
        n = _ie_count(pf.job_title)
        if pf.job_title_search_headline:
            n += 1
        return n
    if section == "seniority":
        return len(pf.job_level) + len(pf.job_function)
    if section == "location_p":
        n = (len(pf.location_country_code) + len(pf.location_continent)
             + len(pf.location_sales_region) + len(pf.location_city))
        if pf.min_connections:
            n += 1
        return n
    return 0


def _section_header(label: str, count: int) -> str:
    """Render the section label + count badge as the expander title."""
    if count > 0:
        return f"{label}  ·  {count} set"
    return label


def _chip_input_textarea(key: str, current: list[str], placeholder: str = "") -> list[str]:
    raw = st.text_area(
        "values",
        value="\n".join(current),
        key=key,
        height=68,
        placeholder=placeholder,
        label_visibility="collapsed",
    )
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _exclude_block(label: str, key: str, current: list[str], options=None,
                   placeholder: str = "") -> list[str]:
    """Hidden behind a 'More' toggle. Returns the list of excluded values."""
    show = st.toggle(f"+ Add exclusions ({len(current)})" if current
                     else "+ Add exclusions",
                     key=f"toggle_{key}", value=bool(current))
    if not show:
        return current  # keep value, just don't show widget
    if options is not None:
        return st.multiselect(
            label, options=options, default=current,
            key=f"{key}_exc", label_visibility="collapsed",
        )
    return _chip_input_textarea(f"{key}_exc", current, placeholder)


# ----- presets -------------------------------------------------------------


PRESETS = {
    "SaaS founders · US/UK": lambda: _preset(
        industry=["Software Development"],
        size_min=11, size_max=200,
        countries_co=["US", "GB"],
        titles=["[Founder]", "[Co-Founder]"],
        levels=["Other", "C-Team"],
    ),
    "Marketing leaders · EU": lambda: _preset(
        industry=["Software Development", "IT Services and IT Consulting",
                  "Marketing and Advertising"],
        size_min=51, size_max=500,
        continents_co=["Europe"],
        titles=["VP Marketing", "Head of Marketing", "CMO", "Marketing Director"],
        functions=["Advertising & Marketing"],
    ),
    "All C-suite · 50-500 employees": lambda: _preset(
        size_min=50, size_max=500,
        levels=["C-Team"],
    ),
}


def _preset(**kw) -> SearchFilters:
    sf = SearchFilters()
    if kw.get("industry"):
        sf.company.industry.include = list(kw["industry"])
    if kw.get("size_min") is not None:
        sf.company.employee_count_min = kw["size_min"]
    if kw.get("size_max") is not None:
        sf.company.employee_count_max = kw["size_max"]
    if kw.get("countries_co"):
        sf.company.hq_country_code = list(kw["countries_co"])
    if kw.get("continents_co"):
        sf.company.hq_continent = list(kw["continents_co"])
    if kw.get("titles"):
        sf.people.job_title.include = list(kw["titles"])
    if kw.get("levels"):
        sf.people.job_level = list(kw["levels"])
    if kw.get("functions"):
        sf.people.job_function = list(kw["functions"])
    return sf


# ----- active-filter chips ------------------------------------------------


def render_active_chips(filters: SearchFilters, container=None) -> None:
    """Show one chip per non-empty filter. Click ✕ to clear that field."""
    c = container or st
    chips = []

    cf, pf = filters.company, filters.people

    if cf.industry.include:
        chips.append(("industry_inc", "Industry", ", ".join(cf.industry.include[:2])
                      + (f" +{len(cf.industry.include)-2}" if len(cf.industry.include) > 2 else "")))
    if cf.industry.exclude:
        chips.append(("industry_exc", "Industry excl",
                      ", ".join(cf.industry.exclude[:2])))
    if cf.employee_count_min is not None or cf.employee_count_max is not None:
        a = cf.employee_count_min or 0
        b = cf.employee_count_max or "∞"
        chips.append(("size", "Size", f"{a}–{b}"))
    if cf.employee_range:
        chips.append(("size_b", "Size", ", ".join(cf.employee_range)))
    if cf.founded_year_min or cf.founded_year_max:
        chips.append(("founded", "Founded",
                      f"{cf.founded_year_min or '…'}–{cf.founded_year_max or '…'}"))
    if cf.hq_country_code:
        chips.append(("hq_country", "HQ country", ", ".join(cf.hq_country_code[:3])
                      + (f" +{len(cf.hq_country_code)-3}" if len(cf.hq_country_code) > 3 else "")))
    if cf.hq_continent:
        chips.append(("hq_cont", "HQ continent", ", ".join(cf.hq_continent)))
    if cf.hq_sales_region:
        chips.append(("hq_sr", "Sales region", ", ".join(cf.hq_sales_region)))
    if cf.hq_city.include:
        chips.append(("hq_city", "City", ", ".join(cf.hq_city.include[:2])))
    if cf.keywords.include:
        chips.append(("kw", "Keywords",
                      ", ".join(cf.keywords.include[:2])))
    if cf.type_.include:
        chips.append(("ctype", "Type", ", ".join(cf.type_.include[:2])))
    if cf.min_linkedin_followers:
        chips.append(("followers", "Min followers", f"≥ {cf.min_linkedin_followers:,}"))
    if cf.name.include:
        chips.append(("cname", "Company name", cf.name.include[0]
                      + (f" +{len(cf.name.include)-1}" if len(cf.name.include) > 1 else "")))

    if pf.job_title.include:
        chips.append(("title", "Title",
                      ", ".join(pf.job_title.include[:2])
                      + (f" +{len(pf.job_title.include)-2}" if len(pf.job_title.include) > 2 else "")))
    if pf.job_level:
        chips.append(("level", "Seniority", ", ".join(pf.job_level)))
    if pf.job_function:
        chips.append(("function", "Function", ", ".join(pf.job_function[:2])))
    if pf.location_country_code:
        chips.append(("p_country", "Person country",
                      ", ".join(pf.location_country_code[:3])))
    if pf.location_city:
        chips.append(("p_city", "Person city", ", ".join(pf.location_city[:2])))
    if pf.min_connections:
        chips.append(("p_conn", "Min connections", f"≥ {pf.min_connections}"))

    if not chips:
        c.markdown(
            f'<p style="color:{design.TEXT_3};font-size:12.5px;margin:6px 0;">'
            f'No active filters. Use the panel on the left or pick a preset.'
            f'</p>',
            unsafe_allow_html=True,
        )
        return

    # Render chips as inline HTML pills. Streamlit doesn't support clickable
    # inline HTML chips with state, so the ✕ is a visual cue; clearing
    # happens by removing values in the panel. For programmatic dismiss we'd
    # need custom JS — out of scope.
    pills_html = "".join([
        f'<span class="bc-chip"><span class="bc-chip-key">{k}</span> '
        f'<span class="bc-chip-val">{v}</span></span>'
        for _, k, v in chips
    ])
    c.markdown(f'<div class="bc-chips">{pills_html}</div>',
               unsafe_allow_html=True)


# ----- main render ---------------------------------------------------------


def render(filters: SearchFilters, container=None) -> SearchFilters:
    """Render filters into the given container. Returns the same filters obj."""
    c = container or st

    with c:
        # ---------- Quick presets ----------
        st.markdown('<p class="bc-eyebrow" style="margin:0 0 6px;">Quick presets</p>',
                    unsafe_allow_html=True)
        cols = st.columns(len(PRESETS))
        for i, (name, builder) in enumerate(PRESETS.items()):
            if cols[i].button(name, key=f"preset_{i}", use_container_width=True):
                st.session_state.filters = builder()
                st.rerun()

        st.markdown('<p class="bc-eyebrow" style="margin:1.4rem 0 4px;">Filters</p>',
                    unsafe_allow_html=True)

        # ============== INDUSTRY =====================================
        with st.expander(_section_header("Industry", _section_count(filters, "industry")),
                         expanded=bool(filters.company.industry.include)):
            filters.company.industry.include = st.multiselect(
                "Industry", options=rd.industries(),
                default=filters.company.industry.include, key="ind_inc",
                placeholder="Search 534 LinkedIn industries",
                label_visibility="collapsed",
            )
            filters.company.industry.exclude = _exclude_block(
                "Industry excl", "ind", filters.company.industry.exclude,
                options=rd.industries(),
            )

        # ============== SIZE =========================================
        with st.expander(_section_header("Company size", _section_count(filters, "size")),
                         expanded=bool(filters.company.employee_count_min
                                       or filters.company.employee_count_max
                                       or filters.company.employee_range)):
            mode = st.radio(
                "Mode", ["Range", "Buckets"], horizontal=True, key="size_mode",
                label_visibility="collapsed",
            )
            if mode == "Range":
                col1, col2 = st.columns(2)
                with col1:
                    mn = st.number_input(
                        "Min employees", min_value=0, max_value=1_000_000,
                        value=int(filters.company.employee_count_min or 0),
                        step=10, key="emp_min",
                    )
                with col2:
                    mx = st.number_input(
                        "Max employees", min_value=0, max_value=1_000_000,
                        value=int(filters.company.employee_count_max or 0),
                        step=10, key="emp_max",
                    )
                filters.company.employee_count_min = mn if mn > 0 else None
                filters.company.employee_count_max = mx if mx > 0 else None
                filters.company.employee_range = []
            else:
                filters.company.employee_range = st.multiselect(
                    "Employee buckets", options=EMPLOYEE_RANGE_BUCKETS,
                    default=filters.company.employee_range, key="emp_buckets",
                    label_visibility="collapsed",
                )
                filters.company.employee_count_min = None
                filters.company.employee_count_max = None

        # ============== FOUNDED =====================================
        with st.expander(_section_header("Founded year",
                                         _section_count(filters, "founded")),
                         expanded=bool(filters.company.founded_year_min
                                       or filters.company.founded_year_max)):
            col1, col2 = st.columns(2)
            with col1:
                mn = st.number_input(
                    "From", min_value=0, max_value=2100,
                    value=int(filters.company.founded_year_min or 0),
                    step=1, key="fy_min",
                )
            with col2:
                mx = st.number_input(
                    "To", min_value=0, max_value=2100,
                    value=int(filters.company.founded_year_max or 0),
                    step=1, key="fy_max",
                )
            filters.company.founded_year_min = mn if mn > 0 else None
            filters.company.founded_year_max = mx if mx > 0 else None

        # ============== COMPANY LOCATION ============================
        with st.expander(_section_header("Company HQ location",
                                         _section_count(filters, "location_co")),
                         expanded=False):
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            filters.company.hq_country_code = st.multiselect(
                "Country", options=country_options,
                default=filters.company.hq_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="hq_country",
            )
            col1, col2 = st.columns(2)
            with col1:
                filters.company.hq_continent = st.multiselect(
                    "Continent", options=rd.continents(),
                    default=filters.company.hq_continent, key="hq_cont",
                )
            with col2:
                filters.company.hq_sales_region = st.multiselect(
                    "Sales region", options=rd.sales_regions(),
                    default=filters.company.hq_sales_region, key="hq_sr",
                )
            filters.company.hq_city.include = _chip_input_textarea(
                "hq_city_inc", filters.company.hq_city.include,
                placeholder="Cities (one per line) — Blitz has no state filter",
            )
            filters.company.hq_city.exclude = _exclude_block(
                "City excl", "hq_city", filters.company.hq_city.exclude,
                placeholder="Cities to exclude",
            )

        # ============== DESCRIPTION & TYPE ==========================
        with st.expander(_section_header("Description & type",
                                         _section_count(filters, "description")),
                         expanded=False):
            st.caption("Description keywords")
            filters.company.keywords.include = _chip_input_textarea(
                "kw_inc", filters.company.keywords.include,
                placeholder="e.g. AI, b2b, fintech (one per line)",
            )
            filters.company.keywords.exclude = _exclude_block(
                "Keywords excl", "kw", filters.company.keywords.exclude,
                placeholder="Keywords to exclude",
            )
            filters.company.type_.include = st.multiselect(
                "Company type", options=rd.company_types(),
                default=filters.company.type_.include, key="ctype_inc",
            )
            filters.company.type_.exclude = _exclude_block(
                "Type excl", "ctype", filters.company.type_.exclude,
                options=rd.company_types(),
            )
            mlf = st.number_input(
                "Min LinkedIn followers", min_value=0, max_value=10_000_000,
                value=int(filters.company.min_linkedin_followers or 0),
                step=100, key="min_followers",
            )
            filters.company.min_linkedin_followers = mlf if mlf > 0 else None

        # ============== COMPANY NAME ================================
        with st.expander(_section_header("Company name",
                                         _section_count(filters, "company_name")),
                         expanded=False):
            filters.company.name.include = _chip_input_textarea(
                "cname_inc", filters.company.name.include,
                placeholder="One name per line. [Brackets] = exact match.",
            )
            filters.company.name.exclude = _exclude_block(
                "Name excl", "cname", filters.company.name.exclude,
                placeholder="Names to exclude",
            )

        # ============== JOB TITLE ===================================
        with st.expander(_section_header("Job title",
                                         _section_count(filters, "title")),
                         expanded=bool(filters.people.job_title.include)):
            filters.people.job_title.include = _chip_input_textarea(
                "title_inc", filters.people.job_title.include,
                placeholder="One title per line. [Founder] = exact match.",
            )
            filters.people.job_title.exclude = _exclude_block(
                "Title excl", "title", filters.people.job_title.exclude,
                placeholder="Titles to exclude (e.g. assistant, intern)",
            )
            filters.people.job_title_search_headline = st.checkbox(
                "Also search LinkedIn headlines for these titles",
                value=filters.people.job_title_search_headline,
                key="title_headline",
            )

        # ============== SENIORITY + FUNCTION =========================
        with st.expander(_section_header("Seniority & function",
                                         _section_count(filters, "seniority")),
                         expanded=bool(filters.people.job_level
                                       or filters.people.job_function)):
            filters.people.job_level = st.multiselect(
                "Seniority", options=rd.job_levels(),
                default=filters.people.job_level, key="job_level",
                placeholder="Pick one or more levels",
            )
            filters.people.job_function = st.multiselect(
                "Department / function", options=rd.job_functions(),
                default=filters.people.job_function, key="job_function",
                placeholder="Pick one or more functions",
            )

        # ============== PERSON LOCATION ==============================
        with st.expander(_section_header("Person location & network",
                                         _section_count(filters, "location_p")),
                         expanded=False):
            country_options = [c["code"] for c in rd.countries()]
            country_labels = {c["code"]: f"{c['code']} — {c['name']}" for c in rd.countries()}
            filters.people.location_country_code = st.multiselect(
                "Country", options=country_options,
                default=filters.people.location_country_code,
                format_func=lambda code: country_labels.get(code, code),
                key="ploc_country",
            )
            col1, col2 = st.columns(2)
            with col1:
                filters.people.location_continent = st.multiselect(
                    "Continent", options=rd.continents(),
                    default=filters.people.location_continent, key="ploc_cont",
                )
            with col2:
                filters.people.location_sales_region = st.multiselect(
                    "Sales region", options=rd.sales_regions(),
                    default=filters.people.location_sales_region, key="ploc_sr",
                )
            filters.people.location_city = _chip_input_textarea(
                "ploc_city", filters.people.location_city,
                placeholder="Cities (one per line)",
            )
            mc = st.number_input(
                "Min LinkedIn connections", min_value=0, max_value=500,
                value=int(filters.people.min_connections or 0),
                step=10, key="min_conn",
            )
            filters.people.min_connections = mc if mc > 0 else None

    return filters
