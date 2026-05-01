"""Filter panel — VSCode-style secondary nav.

Layout: icon rail (always visible) + active-section panel (expands when an
icon is clicked). Only one section open at a time, like a sidebar accordion.

Public API:
- render_rail(filters, container) — draws the icon rail
- render_active_section(filters, container) — draws the active section panel
- render_active_chips(filters, container) — chip bar of all active filter values
- PRESETS dict — quick-preset builders
"""

from __future__ import annotations

import streamlit as st

from app.lib import design, reference_data as rd
from app.lib.filter_model import EMPLOYEE_RANGE_BUCKETS, SearchFilters

# ----- section catalog ----------------------------------------------------


# (key, label, material-icon, count-fn)
SECTIONS: list[tuple[str, str, str]] = [
    ("industry",     "Industry",          ":material/factory:"),
    ("size",         "Company size",      ":material/groups:"),
    ("founded",      "Founded year",      ":material/event:"),
    ("location_co",  "Company HQ",        ":material/business:"),
    ("description",  "Description & type", ":material/description:"),
    ("company_name", "Company name",      ":material/apartment:"),
    ("title",        "Job title",         ":material/work:"),
    ("seniority",    "Seniority & function", ":material/military_tech:"),
    ("location_p",   "Person location",   ":material/person_pin:"),
]


def _section_count(filters: SearchFilters, section: str) -> int:
    cf, pf = filters.company, filters.people
    if section == "industry":
        return len(cf.industry.include) + len(cf.industry.exclude)
    if section == "size":
        n = 1 if cf.employee_range else 0
        if cf.employee_count_min is not None or cf.employee_count_max is not None:
            n += 1
        return n
    if section == "founded":
        return 1 if (cf.founded_year_min or cf.founded_year_max) else 0
    if section == "location_co":
        return (len(cf.hq_country_code) + len(cf.hq_continent)
                + len(cf.hq_sales_region)
                + len(cf.hq_city.include) + len(cf.hq_city.exclude))
    if section == "description":
        return (len(cf.keywords.include) + len(cf.keywords.exclude)
                + len(cf.type_.include) + len(cf.type_.exclude)
                + (1 if cf.min_linkedin_followers else 0))
    if section == "company_name":
        return len(cf.name.include) + len(cf.name.exclude)
    if section == "title":
        n = len(pf.job_title.include) + len(pf.job_title.exclude)
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


# ----- presets ------------------------------------------------------------


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
    "All C-suite · 50-500": lambda: _preset(
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


# ----- helpers ------------------------------------------------------------


def _chip_input(key: str, current: list[str], placeholder: str = "") -> list[str]:
    raw = st.text_area(
        "values", value="\n".join(current), key=key, height=68,
        placeholder=placeholder, label_visibility="collapsed",
    )
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _exclude_block(key: str, current: list[str], options=None,
                   placeholder: str = "") -> list[str]:
    show = st.toggle(
        f"+ Add exclusions ({len(current)})" if current else "+ Add exclusions",
        key=f"toggle_{key}", value=bool(current),
    )
    if not show:
        return current
    if options is not None:
        return st.multiselect(
            "Exclude", options=options, default=current,
            key=f"{key}_exc", label_visibility="collapsed",
        )
    return _chip_input(f"{key}_exc", current, placeholder)


# ----- rail ---------------------------------------------------------------


def render_rail(filters: SearchFilters, container=None) -> None:
    """Vertical icon-only navigation. Click an icon to open that section."""
    active = st.session_state.get("active_filter")

    target = container if container is not None else st
    target.markdown('<div class="bc-filter-rail">', unsafe_allow_html=True)

    for key, label, icon in SECTIONS:
        count = _section_count(filters, key)
        label_with_count = f"{label} · {count}" if count else label
        is_active = (active == key)

        if is_active:
            target.markdown('<div class="bc-filter-rail-active">',
                            unsafe_allow_html=True)
        if target.button(icon, key=f"rail_{key}",
                         help=label_with_count,
                         use_container_width=True):
            st.session_state.active_filter = None if is_active else key
            st.rerun()
        if is_active:
            target.markdown('</div>', unsafe_allow_html=True)

    target.markdown('<div class="bc-filter-rail-divider"></div>',
                    unsafe_allow_html=True)

    if target.button(":material/refresh:", key="rail_reset",
                     help="Reset all filters", use_container_width=True):
        st.session_state.filters = SearchFilters()
        st.session_state.active_filter = None
        st.rerun()

    target.markdown('</div>', unsafe_allow_html=True)


# ----- active section -----------------------------------------------------


def render_active_section(filters: SearchFilters, container=None) -> None:
    """Render the form widgets for whichever section is active."""
    target = container if container is not None else st
    active = st.session_state.get("active_filter")

    if not active:
        target.markdown(
            '<div class="bc-filter-panel">'
            '<div class="bc-filter-panel-empty">'
            'Pick a filter from the rail on the left,<br>or use a preset.'
            '</div></div>',
            unsafe_allow_html=True,
        )
        return

    label = next((l for k, l, _ in SECTIONS if k == active), active)
    count = _section_count(filters, active)

    with target.container(border=True):
        head_col1, head_col2 = st.columns([5, 1])
        with head_col1:
            st.markdown(
                f'<div class="bc-filter-panel-title">{label}'
                f'{" · " + str(count) + " set" if count else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with head_col2:
            if st.button("Close", key="close_active",
                         use_container_width=True):
                st.session_state.active_filter = None
                st.rerun()

        _render_section_widgets(active, filters)


def _render_section_widgets(section: str, filters: SearchFilters) -> None:
    cf, pf = filters.company, filters.people

    if section == "industry":
        cf.industry.include = st.multiselect(
            "Include", options=rd.industries(),
            default=cf.industry.include, key="ind_inc",
            placeholder="Search 534 industries",
        )
        cf.industry.exclude = _exclude_block(
            "ind", cf.industry.exclude, options=rd.industries(),
        )

    elif section == "size":
        mode = st.radio("Mode", ["Range", "Buckets"], horizontal=True,
                        key="size_mode", label_visibility="collapsed")
        if mode == "Range":
            col1, col2 = st.columns(2)
            with col1:
                mn = st.number_input(
                    "Min employees", min_value=0, max_value=1_000_000,
                    value=int(cf.employee_count_min or 0), step=10, key="emp_min",
                )
            with col2:
                mx = st.number_input(
                    "Max employees", min_value=0, max_value=1_000_000,
                    value=int(cf.employee_count_max or 0), step=10, key="emp_max",
                )
            cf.employee_count_min = mn if mn > 0 else None
            cf.employee_count_max = mx if mx > 0 else None
            cf.employee_range = []
        else:
            cf.employee_range = st.multiselect(
                "Buckets", options=EMPLOYEE_RANGE_BUCKETS,
                default=cf.employee_range, key="emp_buckets",
                label_visibility="collapsed",
            )
            cf.employee_count_min = None
            cf.employee_count_max = None

    elif section == "founded":
        col1, col2 = st.columns(2)
        with col1:
            mn = st.number_input(
                "From", min_value=0, max_value=2100,
                value=int(cf.founded_year_min or 0), step=1, key="fy_min",
            )
        with col2:
            mx = st.number_input(
                "To", min_value=0, max_value=2100,
                value=int(cf.founded_year_max or 0), step=1, key="fy_max",
            )
        cf.founded_year_min = mn if mn > 0 else None
        cf.founded_year_max = mx if mx > 0 else None

    elif section == "location_co":
        country_options = [c["code"] for c in rd.countries()]
        country_labels = {c["code"]: f"{c['code']} — {c['name']}"
                          for c in rd.countries()}
        cf.hq_country_code = st.multiselect(
            "Country", options=country_options,
            default=cf.hq_country_code,
            format_func=lambda code: country_labels.get(code, code),
            key="hq_country",
        )
        col1, col2 = st.columns(2)
        with col1:
            cf.hq_continent = st.multiselect(
                "Continent", options=rd.continents(),
                default=cf.hq_continent, key="hq_cont",
            )
        with col2:
            cf.hq_sales_region = st.multiselect(
                "Sales region", options=rd.sales_regions(),
                default=cf.hq_sales_region, key="hq_sr",
            )
        st.caption("City (one per line)")
        cf.hq_city.include = _chip_input(
            "hq_city_inc", cf.hq_city.include,
            placeholder="No state-level filter — country + city only",
        )
        cf.hq_city.exclude = _exclude_block(
            "hq_city", cf.hq_city.exclude,
            placeholder="Cities to exclude",
        )

    elif section == "description":
        st.caption("Description keywords")
        cf.keywords.include = _chip_input(
            "kw_inc", cf.keywords.include,
            placeholder="e.g. AI, b2b, fintech",
        )
        cf.keywords.exclude = _exclude_block(
            "kw", cf.keywords.exclude,
            placeholder="Keywords to exclude",
        )
        cf.type_.include = st.multiselect(
            "Company type", options=rd.company_types(),
            default=cf.type_.include, key="ctype_inc",
        )
        cf.type_.exclude = _exclude_block(
            "ctype", cf.type_.exclude, options=rd.company_types(),
        )
        mlf = st.number_input(
            "Min LinkedIn followers", min_value=0, max_value=10_000_000,
            value=int(cf.min_linkedin_followers or 0), step=100,
            key="min_followers",
        )
        cf.min_linkedin_followers = mlf if mlf > 0 else None

    elif section == "company_name":
        st.caption("Company name")
        cf.name.include = _chip_input(
            "cname_inc", cf.name.include,
            placeholder="One name per line. [Brackets] = exact match.",
        )
        cf.name.exclude = _exclude_block(
            "cname", cf.name.exclude,
            placeholder="Names to exclude",
        )

    elif section == "title":
        st.caption("Job title")
        pf.job_title.include = _chip_input(
            "title_inc", pf.job_title.include,
            placeholder="One title per line. [Founder] = exact match.",
        )
        pf.job_title.exclude = _exclude_block(
            "title", pf.job_title.exclude,
            placeholder="Titles to exclude (e.g. assistant, intern)",
        )
        pf.job_title_search_headline = st.checkbox(
            "Also search LinkedIn headlines for these titles",
            value=pf.job_title_search_headline, key="title_headline",
        )

    elif section == "seniority":
        pf.job_level = st.multiselect(
            "Seniority", options=rd.job_levels(),
            default=pf.job_level, key="job_level",
        )
        pf.job_function = st.multiselect(
            "Department / function", options=rd.job_functions(),
            default=pf.job_function, key="job_function",
        )

    elif section == "location_p":
        country_options = [c["code"] for c in rd.countries()]
        country_labels = {c["code"]: f"{c['code']} — {c['name']}"
                          for c in rd.countries()}
        pf.location_country_code = st.multiselect(
            "Country", options=country_options,
            default=pf.location_country_code,
            format_func=lambda code: country_labels.get(code, code),
            key="ploc_country",
        )
        col1, col2 = st.columns(2)
        with col1:
            pf.location_continent = st.multiselect(
                "Continent", options=rd.continents(),
                default=pf.location_continent, key="ploc_cont",
            )
        with col2:
            pf.location_sales_region = st.multiselect(
                "Sales region", options=rd.sales_regions(),
                default=pf.location_sales_region, key="ploc_sr",
            )
        st.caption("City (one per line)")
        pf.location_city = _chip_input(
            "ploc_city", pf.location_city,
            placeholder="One city per line",
        )
        mc = st.number_input(
            "Min LinkedIn connections", min_value=0, max_value=500,
            value=int(pf.min_connections or 0), step=10, key="min_conn",
        )
        pf.min_connections = mc if mc > 0 else None


# ----- active-filter chip bar (unchanged from before) ---------------------


def render_active_chips(filters: SearchFilters, container=None) -> None:
    target = container if container is not None else st
    chips = []

    cf, pf = filters.company, filters.people

    if cf.industry.include:
        chips.append(("Industry",
                      ", ".join(cf.industry.include[:2])
                      + (f" +{len(cf.industry.include)-2}"
                         if len(cf.industry.include) > 2 else "")))
    if cf.industry.exclude:
        chips.append(("Industry excl",
                      ", ".join(cf.industry.exclude[:2])))
    if cf.employee_count_min is not None or cf.employee_count_max is not None:
        a = cf.employee_count_min or 0
        b = cf.employee_count_max or "∞"
        chips.append(("Size", f"{a}–{b}"))
    if cf.employee_range:
        chips.append(("Size", ", ".join(cf.employee_range)))
    if cf.founded_year_min or cf.founded_year_max:
        chips.append(("Founded",
                      f"{cf.founded_year_min or '…'}–{cf.founded_year_max or '…'}"))
    if cf.hq_country_code:
        chips.append(("HQ country",
                      ", ".join(cf.hq_country_code[:3])
                      + (f" +{len(cf.hq_country_code)-3}"
                         if len(cf.hq_country_code) > 3 else "")))
    if cf.hq_continent:
        chips.append(("HQ continent", ", ".join(cf.hq_continent)))
    if cf.hq_sales_region:
        chips.append(("Sales region", ", ".join(cf.hq_sales_region)))
    if cf.hq_city.include:
        chips.append(("City", ", ".join(cf.hq_city.include[:2])))
    if cf.keywords.include:
        chips.append(("Keywords", ", ".join(cf.keywords.include[:2])))
    if cf.type_.include:
        chips.append(("Type", ", ".join(cf.type_.include[:2])))
    if cf.min_linkedin_followers:
        chips.append(("Followers", f"≥ {cf.min_linkedin_followers:,}"))
    if cf.name.include:
        chips.append(("Company name",
                      cf.name.include[0]
                      + (f" +{len(cf.name.include)-1}"
                         if len(cf.name.include) > 1 else "")))
    if pf.job_title.include:
        chips.append(("Title",
                      ", ".join(pf.job_title.include[:2])
                      + (f" +{len(pf.job_title.include)-2}"
                         if len(pf.job_title.include) > 2 else "")))
    if pf.job_level:
        chips.append(("Seniority", ", ".join(pf.job_level)))
    if pf.job_function:
        chips.append(("Function", ", ".join(pf.job_function[:2])))
    if pf.location_country_code:
        chips.append(("Person country",
                      ", ".join(pf.location_country_code[:3])))
    if pf.location_city:
        chips.append(("Person city", ", ".join(pf.location_city[:2])))
    if pf.min_connections:
        chips.append(("Min connections", f"≥ {pf.min_connections}"))

    if not chips:
        target.markdown(
            f'<p style="color:{design.TEXT_3};font-size:12.5px;margin:6px 0;">'
            f'No active filters yet.</p>',
            unsafe_allow_html=True,
        )
        return

    pills = "".join([
        f'<span class="bc-chip"><span class="bc-chip-key">{k}</span> '
        f'<span class="bc-chip-val">{v}</span></span>'
        for k, v in chips
    ])
    target.markdown(f'<div class="bc-chips">{pills}</div>',
                    unsafe_allow_html=True)
