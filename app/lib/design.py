"""Minimal design system for Blitz Console.

Philosophy: trust Streamlit's defaults. Override only what's necessary
for visual hierarchy, navigation polish, and the few custom layouts
(active-filter chips, run-history rows, brand block).

Streamlit's [theme] in .streamlit/config.toml drives the colors.
This module just covers the gaps.
"""

from __future__ import annotations

import streamlit as st

# Tokens used by inline HTML helpers (chips, run rows, brand)
TEXT = "#0A0A0A"
TEXT_2 = "#525252"
TEXT_3 = "#A1A1AA"
BORDER = "#E5E5E5"
BG_2 = "#FAFAFA"
BG_3 = "#F4F4F5"

FONT_SANS = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Source Sans Pro', "
    "Roboto, 'Helvetica Neue', Arial, sans-serif"
)
FONT_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


_CSS = f"""
<style>
/* Material Symbols so chevron + icon glyphs render (not ligature names). */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght@20,400&display=swap');

.material-symbols-outlined,
[class*="material-symbols"],
[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"] * {{
  font-family: 'Material Symbols Outlined' !important;
  font-feature-settings: 'liga' !important;
  letter-spacing: 0 !important;
}}

/* Hide Streamlit chrome we don't want */
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}

/* Tighter, wider container */
.main .block-container {{
  padding-top: 2.5rem;
  padding-bottom: 4rem;
  max-width: 1280px;
}}

/* Sidebar: fixed width, subtle separator */
[data-testid="stSidebar"] {{
  width: 240px !important;
  min-width: 240px !important;
  max-width: 240px !important;
  border-right: 1px solid {BORDER};
  background: {BG_2};
}}

/* Sidebar nav: tight, clean active state */
[data-testid="stSidebarNav"] a {{
  font-size: 13.5px !important;
  padding: 7px 12px !important;
  border-radius: 6px !important;
  color: {TEXT_2} !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-current="page"] * {{
  background: {TEXT} !important;
  color: white !important;
}}

/* Tabular nums on metrics + monospace blocks */
[data-testid="stMetricValue"] {{
  font-feature-settings: 'tnum' 1;
  font-variant-numeric: tabular-nums;
}}

/* Brand */
.bc-brand {{
  display: flex; align-items: center; gap: 8px;
  padding: 4px 10px 14px 10px;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 8px;
}}
.bc-brand-logo {{
  width: 22px; height: 22px;
  border-radius: 5px;
  background: {TEXT}; color: white;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 11px;
}}
.bc-brand-name {{
  font-size: 14px; font-weight: 600; color: {TEXT};
}}

/* Eyebrow label (small caps) */
.bc-eyebrow {{
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: {TEXT_3};
  margin: 0 0 0.4rem 0;
}}

/* Subtitle under page title */
.subtitle {{
  color: {TEXT_2}; font-size: 14px;
  margin: -0.2rem 0 1.6rem 0;
}}

/* Hairline divider */
.bc-hairline {{
  height: 1px; background: {BORDER};
  margin: 1.6rem 0;
}}

/* Active filter chips */
.bc-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.bc-chip {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 9px;
  background: {BG_3};
  border: 1px solid {BORDER};
  border-radius: 6px;
  font-size: 12px; line-height: 1.3;
}}
.bc-chip-key {{ color: {TEXT_3}; font-size: 11px; }}
.bc-chip-val {{ color: {TEXT}; }}

/* Run row (Home, Run History) */
.bc-run-row {{
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center; gap: 16px;
  padding: 14px 4px;
  border-bottom: 1px solid {BORDER};
  font-size: 13.5px;
}}
.bc-run-row:last-child {{ border-bottom: none; }}
.bc-run-name {{ font-weight: 500; color: {TEXT}; }}
.bc-run-meta {{ color: {TEXT_3}; font-size: 11.5px; margin-top: 2px; }}
.bc-run-stat {{
  text-align: right; font-feature-settings: 'tnum' 1;
}}
.bc-run-stat strong {{ color: {TEXT}; font-weight: 500; }}
.bc-run-stat span {{ color: {TEXT_3}; font-size: 11.5px; margin-left: 3px; }}

/* ICP item */
.bc-icp-item {{
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 11px 4px;
  border-bottom: 1px solid {BORDER};
  font-size: 13.5px;
}}
.bc-icp-item:last-child {{ border-bottom: none; }}
.bc-icp-item span:first-child {{ color: {TEXT}; font-weight: 500; }}
.bc-icp-item span:last-child {{ color: {TEXT_3}; font-size: 11.5px; }}

/* Status dots */
.bc-status-dot {{
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  vertical-align: middle;
}}
.bc-status-running {{
  background: #2563EB;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.18);
  animation: bc-pulse 1.6s ease-in-out infinite;
}}
.bc-status-done {{ background: #16A34A; }}
.bc-status-error {{ background: #DC2626; }}
.bc-status-queued {{ background: {TEXT_3}; }}
.bc-status-cancelled {{ background: #D97706; }}
@keyframes bc-pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}

/* Empty state */
.bc-empty {{
  background: {BG_2};
  border: 1px dashed {BORDER};
  border-radius: 10px;
  padding: 28px 22px;
  text-align: center;
  color: {TEXT_2};
  font-size: 13.5px;
}}
.bc-empty b {{ color: {TEXT}; }}

/* Filter summary card */
.bc-summary {{
  background: {BG_2};
  border-left: 3px solid {TEXT};
  padding: 12px 14px;
  border-radius: 4px;
  font-size: 14px;
  color: {TEXT};
  line-height: 1.5;
}}

/* Sample preview row */
.bc-sample {{
  padding: 10px 4px;
  border-bottom: 1px solid {BORDER};
  font-size: 13px;
}}
.bc-sample:last-child {{ border-bottom: none; }}
.bc-sample-name {{ font-weight: 500; color: {TEXT}; }}
.bc-sample-meta {{ color: {TEXT_3}; font-size: 12px; margin-top: 2px; }}
</style>
"""


def apply() -> None:
    """Inject minimal CSS. Call once per page after st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.markdown(
        '<div class="bc-brand">'
        '<span class="bc-brand-logo">B</span>'
        '<span class="bc-brand-name">Blitz Console</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None,
                eyebrow: str | None = None) -> None:
    if eyebrow:
        st.markdown(f'<p class="bc-eyebrow">{eyebrow}</p>',
                    unsafe_allow_html=True)
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<p class="subtitle">{subtitle}</p>',
                    unsafe_allow_html=True)


def hairline() -> None:
    st.markdown('<div class="bc-hairline"></div>', unsafe_allow_html=True)


def status_dot(status: str) -> str:
    return f'<span class="bc-status-dot bc-status-{status}"></span>'


def empty_state(message_html: str) -> None:
    st.markdown(f'<div class="bc-empty">{message_html}</div>',
                unsafe_allow_html=True)


def summary_box(text: str) -> None:
    """Filter summary card — used at top of Build Search right pane."""
    st.markdown(f'<div class="bc-summary">{text}</div>',
                unsafe_allow_html=True)
