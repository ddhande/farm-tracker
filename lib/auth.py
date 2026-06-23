"""Lightweight individual-login authentication with persistent (cookie) login.

Users are defined in ``.streamlit/secrets.toml`` like this::

    [[auth.users]]
    username = "darshan"
    name = "Darshan"
    password = "choose-a-password"
    admin = true

    [[auth.users]]
    username = "kunal"
    name = "Kunal"
    password = "choose-a-password"

Add ``admin = true`` to let a user delete/edit *anyone's* entries. Non-admin
users can only delete/edit the entries they created themselves.

Login is remembered across page reloads for 30 days using a signed browser
cookie. Optionally set a signing secret in secrets to make the cookie
tamper-proof::

    [auth]
    cookie_secret = "any-long-random-string"

Passwords live only in server-side secrets and are never sent to the browser.
The logged-in username is stored on every record so you can see who added what.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import streamlit as st

try:
    import extra_streamlit_components as stx

    _HAS_COOKIES = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_COOKIES = False

COOKIE_NAME = "farm_auth"
COOKIE_TTL = 60 * 60 * 24 * 30  # 30 days in seconds

DEMO_USERS = [
    {"username": "darshan", "name": "Darshan", "password": "Darshan@123", "admin": True},
    {"username": "kunal", "name": "Kunal", "password": "farm@123"},
]


def _users() -> list[dict]:
    try:
        configured = st.secrets["auth"]["users"]  # type: ignore[index]
        if configured:
            return [dict(u) for u in configured]
    except Exception:
        pass
    return DEMO_USERS


def _find_user(username: str):
    for u in _users():
        if u.get("username") == username:
            return u
    return None


def _verify(username: str, password: str):
    user = _find_user(username)
    if user and hmac.compare_digest(str(user.get("password", "")), password):
        return user
    return None


# ---------------------------------------------------------------------------
# Cookie persistence
# ---------------------------------------------------------------------------

def _cookie_secret() -> str:
    try:
        secret = st.secrets["auth"]["cookie_secret"]  # type: ignore[index]
        if secret:
            return str(secret)
    except Exception:
        pass
    # Stable fallback so cookies survive app restarts even without a configured
    # secret. Set [auth].cookie_secret in secrets for stronger protection.
    return "farm-tracker-default-cookie-secret-please-override"


def _sign(username: str, expiry: int) -> str:
    msg = f"{username}|{expiry}"
    sig = hmac.new(_cookie_secret().encode(), msg.encode(), hashlib.sha256).hexdigest()
    raw = f"{msg}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode()


def _unsign(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, expiry_s, sig = raw.rsplit("|", 2)
        expiry = int(expiry_s)
        expected = hmac.new(
            _cookie_secret().encode(), f"{username}|{expiry}".encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if expiry < int(time.time()):
            return None
        return username
    except Exception:
        return None


def _cookie_manager():
    """Return a single CookieManager for this session.

    Instantiated once per session and kept in session_state. It must NOT be
    cached with @st.cache_resource because creating it issues a frontend
    (widget) call, which is disallowed inside cached functions.
    """
    if not _HAS_COOKIES:
        return None
    cm = st.session_state.get("_cookie_mgr")
    if cm is None:
        try:
            cm = stx.CookieManager(key="farm_auth_cookies")
        except Exception:
            return None
        st.session_state["_cookie_mgr"] = cm
    return cm


def _read_cookie_username():
    cm = _cookie_manager()
    if cm is None:
        return None
    try:
        token = cm.get(COOKIE_NAME)
    except Exception:
        return None
    return _unsign(token) if token else None


def _write_cookie(username: str) -> None:
    cm = _cookie_manager()
    if cm is None:
        return
    try:
        from datetime import datetime, timezone

        expiry = int(time.time()) + COOKIE_TTL
        cm.set(
            COOKIE_NAME,
            _sign(username, expiry),
            expires_at=datetime.fromtimestamp(expiry, tz=timezone.utc),
            key="farm_auth_set",
        )
    except Exception:
        pass


def _clear_cookie() -> None:
    cm = _cookie_manager()
    if cm is None:
        return
    try:
        cm.delete(COOKIE_NAME, key="farm_auth_del")
    except Exception:
        pass


def _user_session(user: dict) -> dict:
    return {
        "username": user["username"],
        "name": user.get("name", user["username"]),
        "admin": bool(user.get("admin", False)),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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
            st.session_state["auth_user"] = _user_session(user)
            _write_cookie(user["username"])
            st.rerun()
        else:
            st.error("Incorrect username or password.")


def require_login() -> bool:
    """Render the login screen if needed. Returns True when authenticated.

    Login persists across reloads via a signed browser cookie.
    """
    if st.session_state.get("auth_user"):
        return True

    # Try to restore a previous session from the cookie.
    username = _read_cookie_username()
    if username:
        user = _find_user(username)
        if user:
            st.session_state["auth_user"] = _user_session(user)
            return True

    _login_form()
    return False


def current_user() -> dict:
    return st.session_state.get("auth_user", {"username": "unknown", "name": "Unknown"})


def current_username() -> str:
    return current_user().get("username", "unknown")


def is_admin() -> bool:
    return bool(current_user().get("admin", False))


def can_modify(record: dict) -> bool:
    """True if the current user may edit/delete this record.

    Admins can modify anything; everyone else only their own entries.
    """
    if is_admin():
        return True
    return bool(record) and record.get("created_by") == current_username()


def logout() -> None:
    _clear_cookie()
    st.session_state.pop("auth_user", None)
    st.rerun()
