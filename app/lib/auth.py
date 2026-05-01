"""Optional password gate for hosted deploys.

When BLITZ_CONSOLE_PASSWORD is set in the environment, every page calls
require_auth() which renders a login form and short-circuits the rest of
the page until the user submits the correct password. Stored only in the
session — no cookies, no DB.

Locally, leave the env var unset and this is a no-op.
"""

from __future__ import annotations

import hmac
import os

import streamlit as st


def require_auth() -> None:
    expected = os.environ.get("BLITZ_CONSOLE_PASSWORD", "").strip()
    if not expected:
        return  # gate disabled

    if st.session_state.get("_auth_ok"):
        return

    st.title("🔒 Blitz Console")
    st.caption("This deployment is password-protected.")
    pw = st.text_input("Password", type="password", key="_auth_pw")
    if st.button("Unlock", type="primary"):
        if hmac.compare_digest(pw or "", expected):
            st.session_state._auth_ok = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()
