"""Sanity-check the bundled reference data files."""

from __future__ import annotations

from app.lib import reference_data as rd


def test_industries_loaded():
    inds = rd.industries()
    assert isinstance(inds, list)
    assert len(inds) >= 500, f"expected ~534 industries, got {len(inds)}"
    # Spot check well-known values
    assert "Software Development" in inds
    assert "IT Services and IT Consulting" in inds
    assert "Banking" in inds


def test_industries_are_unique():
    inds = rd.industries()
    assert len(inds) == len(set(inds)), "duplicate industry strings"


def test_job_levels_match_blitz_enum():
    assert rd.job_levels() == ["C-Team", "VP", "Director", "Manager", "Staff", "Other"]


def test_job_functions_loaded():
    fns = rd.job_functions()
    assert len(fns) >= 20
    assert "Engineering" in fns
    assert "Sales & Business Development" in fns


def test_company_types_loaded():
    types = rd.company_types()
    assert "Privately Held" in types
    assert "Public Company" in types
    assert "Nonprofit" in types


def test_continents_match_blitz_enum():
    assert set(rd.continents()) == {
        "Africa", "Antarctica", "Asia", "Europe",
        "North America", "Oceania", "South America",
    }


def test_sales_regions_match_blitz_enum():
    assert set(rd.sales_regions()) == {"NORAM", "LATAM", "EMEA", "APAC"}


def test_countries_have_iso_alpha2_codes():
    countries = rd.countries()
    assert len(countries) >= 200
    # All codes are 2 chars uppercase
    for c in countries:
        assert isinstance(c["code"], str) and len(c["code"]) == 2
        assert c["code"] == c["code"].upper()
        assert c["name"]


def test_country_helpers():
    name_to_code = rd.country_name_to_code()
    code_to_name = rd.country_code_to_name()
    assert name_to_code["United States"] == "US"
    assert code_to_name["US"] == "United States"
    assert name_to_code["Germany"] == "DE"
