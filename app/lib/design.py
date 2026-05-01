"""Design system for Blitz Console.

Single source of truth for colors, typography, spacing, and the global CSS
override that retrofits Streamlit's default chrome into a quiet, monochrome,
Inter-typed interface. Page modules call `apply()` immediately after
`st.set_page_config(...)`.

Aesthetic: Linear / Vercel — pure greyscale, hairline borders, no shadows,
generous whitespace, confident typography. No emoji except where they carry
information (status dots).
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------- design tokens

# Colors — monochrome only. Accent stays the same color as text on purpose.
BG = "#FFFFFF"
BG_2 = "#FAFAFA"          # cards, sidebar
BG_3 = "#F5F5F5"          # active row, code blocks
BORDER = "#E5E5E5"        # hairline
BORDER_STRONG = "#D4D4D4"
TEXT = "#0A0A0A"          # near-black, never pure
TEXT_2 = "#525252"        # captions, secondary copy
TEXT_3 = "#A3A3A3"        # disabled, helper micro-copy
SUCCESS = "#16A34A"
WARN = "#D97706"
DANGER = "#DC2626"

# Typography
FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace"


# --------------------------------------------------------------------- styles


_CSS = f"""
<style>
/* --- Inter from Google ---------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

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

/* --- Base typography ----------------------------------------------------- */
html, body, [class*="st"], button, input, textarea, select {{
  font-family: {FONT_SANS} !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: -0.005em;
}}
code, pre, .stCode, [data-testid="stCodeBlock"] {{
  font-family: {FONT_MONO} !important;
  font-size: 12.5px !important;
}}

/* --- Page container ------------------------------------------------------ */
.main .block-container {{
  padding-top: 3rem;
  padding-bottom: 4rem;
  max-width: 1180px;
}}
[data-testid="stAppViewContainer"] {{ background: {BG}; }}

/* --- Headings ------------------------------------------------------------ */
h1, .stMarkdown h1 {{
  font-size: 30px !important;
  font-weight: 600 !important;
  letter-spacing: -0.025em !important;
  color: {TEXT} !important;
  margin: 0 0 0.4rem 0 !important;
  line-height: 1.2 !important;
}}
h2, .stMarkdown h2 {{
  font-size: 19px !important;
  font-weight: 600 !important;
  letter-spacing: -0.015em !important;
  color: {TEXT} !important;
  margin: 2rem 0 0.6rem 0 !important;
  line-height: 1.3 !important;
  padding-bottom: 0 !important;
  border-bottom: none !important;
}}
h3, .stMarkdown h3 {{
  font-size: 15px !important;
  font-weight: 600 !important;
  color: {TEXT} !important;
  margin: 1.2rem 0 0.5rem 0 !important;
}}

/* Page subtitle helper class */
.subtitle {{
  color: {TEXT_2};
  font-size: 14px;
  margin-bottom: 2rem;
  margin-top: -0.2rem;
}}

/* --- Body text ----------------------------------------------------------- */
p, .stMarkdown p, label, .stCaption {{
  color: {TEXT};
  font-size: 14px;
  line-height: 1.55;
}}
[data-testid="stCaptionContainer"], small, .caption {{
  color: {TEXT_2} !important;
  font-size: 12.5px !important;
}}

/* --- Sidebar ------------------------------------------------------------- */
[data-testid="stSidebar"] {{
  background: {BG_2};
  border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] > div:first-child {{
  padding-top: 2.5rem;
}}
[data-testid="stSidebarNav"] {{
  background: transparent;
  padding-top: 0.5rem;
}}
[data-testid="stSidebarNav"] ul {{
  padding-left: 0.4rem;
}}
[data-testid="stSidebarNav"] a {{
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {TEXT_2} !important;
  padding: 6px 12px !important;
  border-radius: 6px !important;
  transition: background 120ms ease, color 120ms ease;
}}
[data-testid="stSidebarNav"] a:hover {{
  background: {BG_3} !important;
  color: {TEXT} !important;
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background: {TEXT} !important;
  color: {BG} !important;
}}
[data-testid="stSidebar"] h3 {{
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: uppercase;
  letter-spacing: 0.06em !important;
  color: {TEXT_3} !important;
  margin-top: 1.5rem !important;
}}

/* --- Buttons ------------------------------------------------------------- */
.stButton > button, .stDownloadButton > button {{
  font-family: {FONT_SANS} !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  letter-spacing: -0.005em !important;
  padding: 0.45rem 0.95rem !important;
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
  background: {BG_2} !important;
  border-color: {BORDER_STRONG} !important;
  color: {TEXT} !important;
}}
.stButton > button:focus, .stDownloadButton > button:focus {{
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(10, 10, 10, 0.08) !important;
}}
.stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
  background: {TEXT} !important;
  color: {BG} !important;
  border-color: {TEXT} !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: #262626 !important;
  border-color: #262626 !important;
}}
.stButton > button:disabled {{
  background: {BG_3} !important;
  color: {TEXT_3} !important;
  border-color: {BORDER} !important;
}}

/* --- Inputs (text, number, textarea, select) ----------------------------- */
input, textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div {{
  font-size: 13.5px !important;
  background: {BG} !important;
}}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{
  border-radius: 6px !important;
  border: 1px solid {BORDER} !important;
  box-shadow: none !important;
  transition: border-color 120ms ease, box-shadow 120ms ease;
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
  font-size: 12px !important;
  font-weight: 500 !important;
}}
[data-baseweb="tag"] svg {{ fill: {BG} !important; }}

/* --- Metric cards -------------------------------------------------------- */
[data-testid="stMetric"] {{
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: 8px;
  padding: 16px 18px;
}}
[data-testid="stMetricLabel"] {{
  color: {TEXT_2} !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.06em !important;
}}
[data-testid="stMetricValue"] {{
  color: {TEXT} !important;
  font-size: 26px !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
  font-feature-settings: 'tnum' 1;
}}
[data-testid="stMetricDelta"] {{
  font-size: 11.5px !important;
  font-weight: 500 !important;
}}

/* --- Expanders ----------------------------------------------------------- */
[data-testid="stExpander"] {{
  border: 1px solid {BORDER} !important;
  border-radius: 8px !important;
  background: {BG} !important;
}}
[data-testid="stExpander"] details summary {{
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {TEXT} !important;
  padding: 10px 14px !important;
}}
[data-testid="stExpander"] details summary:hover {{
  background: {BG_2} !important;
}}

/* Sidebar expanders look denser */
[data-testid="stSidebar"] [data-testid="stExpander"] {{
  border: none !important;
  border-bottom: 1px solid {BORDER} !important;
  border-radius: 0 !important;
}}
[data-testid="stSidebar"] [data-testid="stExpander"] details summary {{
  padding: 14px 4px !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  color: {TEXT_2} !important;
}}

/* --- Tabs ---------------------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {{
  gap: 6px;
  border-bottom: 1px solid {BORDER};
}}
.stTabs [data-baseweb="tab"] {{
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {TEXT_2} !important;
  padding: 8px 14px !important;
  border-radius: 0 !important;
  background: transparent !important;
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
  line-height: 1.55 !important;
  color: {TEXT} !important;
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
  border-radius: 8px !important;
}}

/* --- Alert boxes (info, success, warning, error) ------------------------- */
[data-testid="stAlert"] {{
  border-radius: 8px !important;
  border: 1px solid {BORDER} !important;
  background: {BG_2} !important;
  font-size: 13.5px !important;
  padding: 12px 14px !important;
}}

/* --- Checkbox + radio --------------------------------------------------- */
[data-testid="stCheckbox"] label, [data-testid="stRadio"] label {{
  font-size: 13.5px !important;
  color: {TEXT} !important;
}}

/* --- Custom helpers ------------------------------------------------------ */
.bc-eyebrow {{
  font-size: 11.5px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: {TEXT_3};
  margin: 0 0 0.4rem 0;
}}
.bc-card {{
  background: {BG};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 20px 22px;
}}
.bc-card-muted {{
  background: {BG_2};
  border: 1px solid {BORDER};
  border-radius: 10px;
  padding: 18px 20px;
}}
.bc-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  background: {BG_3};
  color: {TEXT};
}}
.bc-pill-success {{ background: #DCFCE7; color: #14532D; }}
.bc-pill-warn {{ background: #FEF3C7; color: #78350F; }}
.bc-pill-danger {{ background: #FEE2E2; color: #7F1D1D; }}
.bc-pill-mono {{ background: {BG_3}; color: {TEXT_2}; font-family: {FONT_MONO}; }}

.bc-hairline {{
  height: 1px;
  background: {BORDER};
  margin: 1.5rem 0;
}}

.bc-stack > * + * {{ margin-top: 0.6rem; }}

.bc-num {{
  font-feature-settings: 'tnum' 1;
  font-variant-numeric: tabular-nums;
}}

.bc-status-dot {{
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}}
.bc-status-running {{ background: #2563EB; box-shadow: 0 0 0 3px rgba(37,99,235,0.18); }}
.bc-status-done {{ background: {SUCCESS}; }}
.bc-status-error {{ background: {DANGER}; }}
.bc-status-queued {{ background: {TEXT_3}; }}
.bc-status-cancelled {{ background: {WARN}; }}
</style>
"""


def apply() -> None:
    """Inject global CSS. Call once per page, after st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------- shared components


def page_header(title: str, subtitle: str | None = None, eyebrow: str | None = None) -> None:
    """Title block at the top of a page.

    Eyebrow is small uppercase label above the title (e.g. section name).
    """
    if eyebrow:
        st.markdown(f'<p class="bc-eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)


def hairline() -> None:
    st.markdown('<div class="bc-hairline"></div>', unsafe_allow_html=True)


def pill(text: str, variant: str = "default") -> str:
    """Returns inline HTML for a pill. Use inside st.markdown(unsafe_allow_html=True).

    variant ∈ {default, success, warn, danger, mono}
    """
    cls = "bc-pill"
    if variant == "success":
        cls += " bc-pill-success"
    elif variant == "warn":
        cls += " bc-pill-warn"
    elif variant == "danger":
        cls += " bc-pill-danger"
    elif variant == "mono":
        cls += " bc-pill-mono"
    return f'<span class="{cls}">{text}</span>'


def status_dot(status: str) -> str:
    """Returns inline HTML status dot. status: running|done|error|queued|cancelled."""
    cls = f"bc-status-dot bc-status-{status}"
    return f'<span class="{cls}"></span>'


def num(n: int | float | str) -> str:
    """Wrap a number in tabular-nums span for clean alignment."""
    return f'<span class="bc-num">{n}</span>'
