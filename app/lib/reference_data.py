"""Load static reference data (industries, functions, levels, etc.) once.

Cached by Streamlit's @st.cache_data when called from a UI module.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=None)
def industries() -> list[str]:
    return json.loads((DATA_DIR / "industries.json").read_text())


@lru_cache(maxsize=None)
def job_functions() -> list[str]:
    return json.loads((DATA_DIR / "job_functions.json").read_text())


@lru_cache(maxsize=None)
def job_levels() -> list[str]:
    return json.loads((DATA_DIR / "job_levels.json").read_text())


@lru_cache(maxsize=None)
def company_types() -> list[str]:
    return json.loads((DATA_DIR / "company_types.json").read_text())


@lru_cache(maxsize=None)
def continents() -> list[str]:
    return json.loads((DATA_DIR / "continents.json").read_text())


@lru_cache(maxsize=None)
def sales_regions() -> list[str]:
    return json.loads((DATA_DIR / "sales_regions.json").read_text())


@lru_cache(maxsize=None)
def countries() -> list[dict]:
    """List of {code, name}."""
    return json.loads((DATA_DIR / "countries.json").read_text())


def country_code_to_name() -> dict[str, str]:
    return {c["code"]: c["name"] for c in countries()}


def country_name_to_code() -> dict[str, str]:
    return {c["name"]: c["code"] for c in countries()}
