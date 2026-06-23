"""Lightweight individual-login authentication.

Users are defined in ``.streamlit/secrets.toml`` like this::

    [[auth.users]]
    username = "darshan"
    name = "Darshan"
    password = "choose-a-password"

    [[auth.users]]
    username = "kunal"
    name = "Kunal"
    password = "choose-a-password"

If no users are configured (e.g. running locally for the first time), two
accounts are available so you can try the app immediately:

    darshan / farm123      and      kunal / farm123

Passwords live only in server-side secrets and are never sent to the browser.
The logged-in username is stored on every record so you can see who added what.
"""

from __future__ import annotations

import hmac

import streamlit as st

DEMO_USERS = [
    {"username": "darshan", "name": "Darshan", "password": "farm123"},
    {"username": "kunal", "name": "Kunal", "password": "farm123"},
]


def _users() -> list[dict]:
    try:
        configured = st.secrets["auth"]["users"]  # type: ignore[index]
        if configured:
            return [dict(u) for u in configured]
    except Exception:
        pass
    return DEMO_USERS


def _verify(username: str, password: str):
    for u in _users():
        if u.get("username") == username and hmac.compare_digest(
            str(u.get("password", "")), password
        ):
            return u
    return None


def _login_form() -> None:
    st.markdown("## 🌾 Farm Tracker — Sign in")
    st.caption("Track your farm expenses, harvest, yield and profit in one place.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
    if submitted:
        user = _verify(username.strip(), password)
        if user:
            st.session_state["auth_user"] = {
                "username": user["username"],
                "name": user.get("name", user["username"]),
            }
            st.rerun()
        else:
            st.error("Incorrect username or password.")


def require_login() -> bool:
    """Render the login screen if needed. Returns True when authenticated."""
    if st.session_state.get("auth_user"):
        return True
    _login_form()
    return False


def current_user() -> dict:
    return st.session_state.get("auth_user", {"username": "unknown", "name": "Unknown"})


def current_username() -> str:
    return current_user().get("username", "unknown")


def logout() -> None:
    st.session_state.pop("auth_user", None)
    st.rerun()
