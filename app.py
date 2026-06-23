"""Farm Tracker — document farm expenses, harvest, yield and profit.

Run locally:   streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from lib import config, db
from lib.auth import current_user, logout, require_login
from views import bills, crops, dashboard, expenses, harvest, lifecycle

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    if not require_login():
        return

    db.init()
    user = current_user()

    with st.sidebar:
        st.markdown(f"### {config.APP_ICON} {config.APP_TITLE}")
        st.caption(f"Signed in as **{user['name']}**")
        if db.is_shared():
            st.caption("🟢 Shared mode — your partner sees updates too.")
        else:
            st.caption("🟡 Local mode — data saved on this computer only.")

    pages = [
        st.Page(dashboard.render, title="Dashboard", icon="📊", url_path="dashboard", default=True),
        st.Page(expenses.render, title="Expenses", icon="🧾", url_path="expenses"),
        st.Page(harvest.render, title="Harvest & Yield", icon="🌾", url_path="harvest"),
        st.Page(crops.render, title="Crops & Seasons", icon="🌱", url_path="crops"),
        st.Page(lifecycle.render, title="Crop Lifecycle (SOP)", icon="📅", url_path="lifecycle"),
        st.Page(bills.render, title="Bills & Receipts", icon="📁", url_path="bills"),
    ]
    nav = st.navigation(pages)

    with st.sidebar:
        st.divider()
        if st.button("Sign out", width="stretch"):
            logout()

    nav.run()


main()
