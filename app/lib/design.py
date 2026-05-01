"""Design system for Blitz Console.

Single source of truth for colors, typography, spacing, and the global CSS
override that retrofits Streamlit's default chrome into a quiet, monochrome,
Inter-typed interface. Page modules call `apply()` immediately after
`st.set_page_config(...)`.

Aesthetic: Linear / Vercel — pure greyscale, hairline borders, no shadows,
generous whitespace, confident typography.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------- design tokens

BG = "#FFFFFF"
BG_2 = "#FAFAFA"
BG_3 = "#F4F4F5"
BG_HOVER = "#F0F0F0"
BORDER = "#E7E5E4"
BORDER_STRONG = "#D6D3D1"
TEXT = "#0A0A0A"
TEXT_2 = "#525252"
TEXT_3 = "#A1A1AA"
TEXT_4 = "#D4D4D8"
SUCCESS = "#16A34A"
WARN = "#D97706"
DANGER = "#DC2626"

FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace"


# --------------------------------------------------------------------- styles


_CSS = f"""
<style>
/* --- Fonts --------------------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,400,0,0&display=block');

/* --- Hide Streamlit chrome ----------------------------------------------- */
#MainMenu {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
  background: transparent;
  height: 0;
}}
footer {{ visibility: hidden; }}
[data-testid="stToolbar"] {{ display: none; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="stStatusWidget"] {{ display: none; }}
.viewerBadge_container__1QSob {{ display: none; }}

/* Hide the sidebar collapse button (we keep sidebar open) */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {{ display: none !important; }}

/* --- Base typography (scoped to skip icon elements) --------------------- */
html, body, [data-testid="stApp"], button, input, textarea, select,
.stMarkdown, p, h1, h2, h3, h4, h5, h6, span, div, label, a {{
  font-family: {FONT_SANS};
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: -0.005em;
}}

/* CRITICAL: keep icon fonts on Material classes — never override these */
.material-icons,
.material-icons-outlined,
.material-symbols-outlined,
.material-symbols-rounded,
.material-symbols-sharp,
[class*="material-symbols"],
[class*="material-icons"],
[data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] *,
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] *,
[data-testid="stMarkdownContainer"] .material-icons,
[data-testid="stMarkdownContainer"] [class*="material-symbols"] {{
  font-family: 'Material Symbols Outlined', 'Material Icons' !important;
  font-feature-settings: 'liga' !important;
  font-style: normal !important;
  font-weight: normal !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  word-wrap: normal !important;
  white-space: nowrap !important;
  direction: ltr !important;
  -webkit-font-feature-settings: 'liga' !important;
  -webkit-font-smoothing: antialiased !important;
}}

code, pre, [data-testid="stCodeBlock"], [data-testid="stCodeBlock"] * {{
  font-family: {FONT_MONO} !important;
  font-size: 12.5px !important;
  letter-spacing: 0 !important;
}}

/* --- Page container ------------------------------------------------------ */
.main .block-container {{
  padding-top: 3rem;
  padding-bottom: 5rem;
  max-width: 1140px;
}}
[data-testid="stAppViewContainer"] {{ background: {BG}; }}
[data-testid="stMain"] {{ background: {BG}; }}

/* --- Headings ------------------------------------------------------------ */
h1, .stMarkdown h1 {{
  font-size: 32px !important;
  font-weight: 600 !important;
  letter-spacing: -0.028em !important;
  color: {TEXT} !important;
  margin: 0 0 0.4rem 0 !important;
  line-height: 1.15 !important;
}}
h2, .stMarkdown h2 {{
  font-size: 18px !important;
  font-weight: 600 !important;
  letter-spacing: -0.015em !important;
  color: {TEXT} !important;
  margin: 2.5rem 0 0.8rem 0 !important;
  line-height: 1.3 !important;
  padding: 0 !important;
  border: none !important;
}}
h3, .stMarkdown h3 {{
  font-size: 14px !important;
  font-weight: 600 !important;
  color: {TEXT} !important;
  margin: 1.2rem 0 0.5rem 0 !important;
  letter-spacing: -0.01em !important;
}}

.subtitle {{
  color: {TEXT_2};
  font-size: 14.5px;
  margin: -0.2rem 0 2.4rem 0;
  line-height: 1.5;
  max-width: 60ch;
}}

/* --- Body text ----------------------------------------------------------- */
p, .stMarkdown p, label {{
  color: {TEXT};
  font-size: 13.5px;
  line-height: 1.6;
}}
[data-testid="stCaptionContainer"], small {{
  color: {TEXT_2} !important;
  font-size: 12.5px !important;
}}

/* --- Sidebar ------------------------------------------------------------- */
[data-testid="stSidebar"] {{
  background: {BG_2};
  border-right: 1px solid {BORDER};
  width: 264px !important;
  min-width: 264px !important;
  max-width: 264px !important;
}}
[data-testid="stSidebar"] > div:first-child {{
  padding-top: 1.5rem;
  padding-left: 0.6rem;
  padding-right: 0.6rem;
}}

/* Hide Streamlit's auto sidebar header (filename garbage like keyboard_double_arrow) */
[data-testid="stSidebarHeader"] {{ display: none !important; }}
[data-testid="stSidebar"] [data-testid="stIconMaterial"]:has-text("keyboard_double_arrow_left") {{
  display: none !important;
}}

/* Sidebar brand area we add manually */
.bc-brand {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 18px 10px;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 12px;
}}
.bc-brand-logo {{
  width: 22px; height: 22px;
  border-radius: 5px;
  background: {TEXT};
  display: inline-flex; align-items: center; justify-content: center;
  color: {BG};
  font-weight: 700;
  font-size: 11px;
  letter-spacing: -0.02em;
}}
.bc-brand-name {{
  font-size: 14px;
  font-weight: 600;
  color: {TEXT};
  letter-spacing: -0.015em;
}}

/* Sidebar nav links */
[data-testid="stSidebarNav"] {{
  background: transparent;
  padding: 0.4rem 0 0 0 !important;
}}
[data-testid="stSidebarNav"] ul {{
  padding: 0 !important;
  margin: 0 !important;
  list-style: none;
}}
[data-testid="stSidebarNav"] li {{
  margin: 1px 0 !important;
}}
[data-testid="stSidebarNav"] a {{
  display: flex !important;
  align-items: center !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {TEXT_2} !important;
  padding: 7px 12px !important;
  border-radius: 6px !important;
  transition: background 120ms ease, color 120ms ease !important;
  text-decoration: none !important;
}}
[data-testid="stSidebarNav"] a:hover {{
  background: {BG_HOVER} !important;
  color: {TEXT} !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background: {TEXT} !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[aria-current="page"] *,
[data-testid="stSidebarNav"] a[aria-current="page"] span,
[data-testid="stSidebarNav"] a[aria-current="page"] p {{
  color: {BG} !important;
}}
/* Hide bullet markers if any */
[data-testid="stSidebarNav"] a > span:first-child {{
  display: none !important;
}}

/* Sidebar section headings (Filters etc.) */
[data-testid="stSidebar"] h3 {{
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.08em !important;
  color: {TEXT_3} !important;
  margin: 1.5rem 0 0.8rem 0 !important;
  padding-left: 4px;
}}

/* Sidebar expanders — flat with bottom border, no card */
[data-testid="stSidebar"] [data-testid="stExpander"] {{
  border: none !important;
  border-bottom: 1px solid {BORDER} !important;
  border-radius: 0 !important;
  background: transparent !important;
  margin: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
  padding: 13px 4px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: {TEXT_2} !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
  color: {TEXT} !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
  padding-left: 4px !important;
  padding-right: 4px !important;
  padding-bottom: 12px !important;
}}

/* --- Buttons ------------------------------------------------------------- */
.stButton > button, .stDownloadButton > button {{
  font-family: {FONT_SANS} !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: -0.005em !important;
  padding: 0.5rem 1rem !important;
  border-radius: 6px !important;
  border: 1px solid {BORDER} !important;
  background: {BG} !important;
  color: {TEXT} !important;
  transition: all 120ms ease !important;
  box-shadow: none !important;
  height: auto !important;
  min-height: 36px !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  background: {BG_HOVER} !important;
  border-color: {BORDER_STRONG} !important;
  color: {TEXT} !important;
}}
.stButton > button:active, .stDownloadButton > button:active {{
  background: {BG_3} !important;
}}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.08) !important;
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {{
  background: {TEXT} !important;
  color: {BG} !important;
  border-color: {TEXT} !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: #1F1F1F !important;
  border-color: #1F1F1F !important;
}}
.stButton > button:disabled,
.stDownloadButton > button:disabled {{
  background: {BG_2} !important;
  color: {TEXT_3} !important;
  border-color: {BORDER} !important;
  cursor: not-allowed !important;
}}

/* --- Inputs -------------------------------------------------------------- */
input, textarea {{
  font-size: 13.5px !important;
  background: {BG} !important;
  color: {TEXT} !important;
}}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
  border-radius: 6px !important;
  border: 1px solid {BORDER} !important;
  box-shadow: none !important;
  transition: border-color 120ms ease, box-shadow 120ms ease !important;
  background: {BG} !important;
}}
[data-baseweb="input"]:hover,
[data-baseweb="textarea"]:hover,
[data-baseweb="select"] > div:hover {{
  border-color: {BORDER_STRONG} !important;
}}
[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within,
[data-baseweb="select"]:focus-within > div {{
  border-color: {TEXT} !important;
  box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.06) !important;
}}

/* Multiselect chips */
[data-baseweb="tag"] {{
  background: {TEXT} !important;
  color: {BG} !important;
  border-radius: 4px !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em !important;
}}
[data-baseweb="tag"] svg, [data-baseweb="tag"] *, [data-baseweb="tag"] [role="presentation"] {{
  color: {BG} !important;
  fill: {BG} !important;
}}

/* Number input +/- buttons cleaner */
[data-testid="stNumberInputContainer"] button {{
  border-radius: 4px !important;
  background: {BG_2} !important;
  border: 1px solid {BORDER} !important;
  color: {TEXT_2} !important;
}}
[data-testid="stNumberInputContainer"] button:hover {{
  background: {BG_HOVER} !important;
  color: {TEXT} !important;
}}

/* --- Metric cards -------------------------------------------------------- */
[data-testid="stMetric"] {{
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 16px 18px 18px 18px;
  transition: border-color 120ms ease;
}}
[data-testid="stMetric"]:hover {{
  border-color: {BORDER_STRONG};
}}
[data-testid="stMetricLabel"] {{
  color: {TEXT_2} !important;
  margin-bottom: 6px !important;
}}
[data-testid="stMetricLabel"] p {{
  color: {TEXT_2} !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.08em !important;
}}
[data-testid="stMetricValue"] {{
  color: {TEXT} !important;
  font-size: 28px !important;
  font-weight: 600 !important;
  letter-spacing: -0.025em !important;
  font-feature-settings: 'tnum' 1;
  line-height: 1.1 !important;
}}
[data-testid="stMetricValue"] div {{
  font-size: 28px !important;
  font-weight: 600 !important;
  letter-spacing: -0.025em !important;
}}

/* --- Expanders (main area) ---------------------------------------------- */
.main [data-testid="stExpander"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 10px !important;
  background: {BG} !important;
  transition: border-color 120ms ease;
  margin-bottom: 0.6rem;
}}
.main [data-testid="stExpander"]:hover {{
  border-color: {BORDER_STRONG} !important;
}}
.main [data-testid="stExpander"] summary {{
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: {TEXT} !important;
  padding: 12px 16px !important;
  letter-spacing: -0.01em !important;
}}
.main [data-testid="stExpander"] summary:hover {{
  background: {BG_2} !important;
}}
.main [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
  padding: 8px 16px 16px 16px !important;
}}

/* --- Tabs ---------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {{
  gap: 4px;
  border-bottom: 1px solid {BORDER};
  margin-bottom: 1.5rem;
}}
.stTabs [data-baseweb="tab"] {{
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {TEXT_2} !important;
  padding: 10px 14px !important;
  border-radius: 0 !important;
  background: transparent !important;
  border: none !important;
  transition: color 120ms ease;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: {TEXT} !important;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
  color: {TEXT} !important;
  border-bottom: 2px solid {TEXT} !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{ background: {TEXT} !important; }}

/* --- Code / JSON --------------------------------------------------------- */
[data-testid="stCodeBlock"] {{
  background: {BG_2} !important;
  border: 1px solid {BORDER} !important;
  border-radius: 8px !important;
}}
[data-testid="stCodeBlock"] pre {{
  font-size: 12px !important;
  line-height: 1.6 !important;
  color: {TEXT} !important;
  padding: 14px 16px !important;
}}

/* --- Dividers ------------------------------------------------------------ */
hr, [data-testid="stDivider"] {{
  border: none !important;
  border-top: 1px solid {BORDER} !important;
  margin: 1.5rem 0 !important;
}}

/* --- DataFrames ---------------------------------------------------------- */
[data-testid="stDataFrame"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 10px !important;
}}

/* --- Alerts -------------------------------------------------------------- */
[data-testid="stAlert"] {{
  border-radius: 10px !important;
  border: 1px solid {BORDER} !important;
  background: {BG_2} !important;
  font-size: 13px !important;
  padding: 12px 14px !important;
}}
[data-testid="stAlert"] p {{ font-size: 13px !important; }}

/* --- Checkbox / radio / toggle ------------------------------------------ */
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label {{
  font-size: 13.5px !important;
  color: {TEXT} !important;
}}
[data-testid="stRadio"] [role="radiogroup"] {{
  gap: 0.75rem !important;
}}

/* --- Selectbox/multiselect dropdown panel ------------------------------- */
[role="listbox"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 8px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.06) !important;
  font-size: 13px !important;
}}
[role="option"] {{ font-size: 13px !important; }}

/* --- Helpers ------------------------------------------------------------- */
.bc-eyebrow {{
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: {TEXT_3};
  margin: 0 0 0.5rem 0;
}}
.bc-card {{
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 18px 20px;
  transition: border-color 120ms ease;
}}
.bc-card:hover {{ border-color: {BORDER_STRONG}; }}
.bc-card-muted {{
  background: {BG_2};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 18px 20px;
  color: {TEXT_2};
  font-size: 13.5px;
}}
.bc-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  background: {BG_3};
  color: {TEXT};
  letter-spacing: -0.005em;
}}
.bc-pill-success {{ background: #DCFCE7; color: #14532D; }}
.bc-pill-warn {{ background: #FEF3C7; color: #78350F; }}
.bc-pill-danger {{ background: #FEE2E2; color: #7F1D1D; }}
.bc-pill-mono {{ background: {BG_3}; color: {TEXT_2}; font-family: {FONT_MONO}; }}

.bc-hairline {{
  height: 1px;
  background: {BORDER};
  margin: 2rem 0;
}}

.bc-num {{
  font-feature-settings: 'tnum' 1;
  font-variant-numeric: tabular-nums;
}}

.bc-status-dot {{
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 10px;
  vertical-align: middle;
  flex-shrink: 0;
}}
.bc-status-running {{ background: #2563EB; box-shadow: 0 0 0 3px rgba(37,99,235,0.18); animation: bc-pulse 1.6s ease-in-out infinite; }}
.bc-status-done {{ background: {SUCCESS}; }}
.bc-status-error {{ background: {DANGER}; }}
.bc-status-queued {{ background: {TEXT_3}; }}
.bc-status-cancelled {{ background: {WARN}; }}
@keyframes bc-pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.55; }}
}}

/* Run-row layout */
.bc-run-row {{
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  align-items: center;
  gap: 16px;
  padding: 14px 4px;
  border-bottom: 1px solid {BORDER};
  font-size: 13.5px;
}}
.bc-run-row:last-child {{ border-bottom: none; }}
.bc-run-name {{ font-weight: 500; color: {TEXT}; }}
.bc-run-meta {{ color: {TEXT_3}; font-size: 11.5px; margin-top: 2px; }}
.bc-run-stat {{
  text-align: right;
  font-feature-settings: 'tnum' 1;
  font-variant-numeric: tabular-nums;
}}
.bc-run-stat strong {{ color: {TEXT}; font-weight: 500; }}
.bc-run-stat span {{ color: {TEXT_3}; font-size: 11.5px; margin-left: 3px; }}

/* ICP item */
.bc-icp-item {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 11px 4px;
  border-bottom: 1px solid {BORDER};
  font-size: 13.5px;
}}
.bc-icp-item:last-child {{ border-bottom: none; }}
.bc-icp-item span:first-child {{ color: {TEXT}; font-weight: 500; }}
.bc-icp-item span:last-child {{ color: {TEXT_3}; font-size: 11.5px; }}

/* Empty state */
.bc-empty {{
  background: {BG_2};
  border: 1px dashed {BORDER_STRONG};
  border-radius: 10px;
  padding: 32px 24px;
  text-align: center;
  color: {TEXT_2};
  font-size: 13.5px;
}}
.bc-empty b {{ color: {TEXT}; font-weight: 600; }}
</style>
"""


def apply() -> None:
    """Inject global CSS. Call once per page, after st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    """Render the brand at the top of the sidebar. Call inside `with st.sidebar:`."""
    st.markdown(
        '<div class="bc-brand">'
        '<span class="bc-brand-logo">B</span>'
        '<span class="bc-brand-name">Blitz Console</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Title block: eyebrow → title → subtitle."""
    if eyebrow:
        st.markdown(f'<p class="bc-eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)


def hairline() -> None:
    st.markdown('<div class="bc-hairline"></div>', unsafe_allow_html=True)


def pill(text: str, variant: str = "default") -> str:
    cls = "bc-pill"
    if variant in ("success", "warn", "danger", "mono"):
        cls += f" bc-pill-{variant}"
    return f'<span class="{cls}">{text}</span>'


def status_dot(status: str) -> str:
    cls = f"bc-status-dot bc-status-{status}"
    return f'<span class="{cls}"></span>'


def empty_state(message_html: str) -> None:
    st.markdown(f'<div class="bc-empty">{message_html}</div>', unsafe_allow_html=True)
