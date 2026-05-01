VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
STREAMLIT := $(VENV)/bin/streamlit

.PHONY: help install run test test-live test-all clean

help:
	@echo "Targets:"
	@echo "  install     Create venv + install deps + install git hooks"
	@echo "  run         Launch Streamlit at http://localhost:8501"
	@echo "  test        Run unit + smoke tests (no API calls)"
	@echo "  test-live   + free live API healthcheck (needs BLITZ_API_KEY)"
	@echo "  test-all    + opt-in count tests (each costs 1 credit)"
	@echo "  clean       Remove venv, db, logs, runs"

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	bash scripts/install-hooks.sh

run:
	$(STREAMLIT) run app/Home.py

test:
	$(PYTEST) tests/ -v

test-live:
	$(PYTEST) tests/ -v

test-all:
	BLITZ_RUN_LIVE_COUNT_TESTS=1 $(PYTEST) tests/ -v

clean:
	rm -rf $(VENV) blitz.db blitz.db-journal *.log runs/ leads_*.json leads_*.csv leads_*.raw
