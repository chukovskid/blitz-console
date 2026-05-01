"""Pytest setup: project root on sys.path, fake API key for AppTest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Use a dummy key for tests that don't hit the network. Live tests override.
os.environ.setdefault("BLITZ_API_KEY", "blitz-test-00000000-0000-0000-0000-000000000000")
