"""Bills: browse and open uploaded bills/receipts attached to expenses."""

from __future__ import annotations

import os

import streamlit as st

from lib import config, db
from views.common import crop_lookup


def render() -> None:
    st.header("📁 Bills & Receipts")
    st.caption("All uploaded bills, grouped with their expense. Click to open.")

    expenses = [e for e in db.list_expenses() if e.get("bill_path")]
    if not expenses:
        st.info("No bills uploaded yet. Attach a bill when adding an expense.")
        return

    lookup = crop_lookup()
    for e in expenses:
        crop = lookup.get(e.get("crop_id"), "—")
        label = (
            f"{e['date']} · {e['category']} · {config.money(e['amount'])}"
            f" · {e.get('vendor') or 'No vendor'}"
        )
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{label}**")
                st.caption(f"{e.get('description') or ''}  ·  Crop: {crop}  ·  Added by: {e.get('created_by')}")
            with c2:
                url = db.bill_url(e["bill_path"])
                _render_bill(url, e["bill_path"])


def _render_bill(url, path) -> None:
    if not url:
        st.caption("File unavailable.")
        return
    is_image = str(path).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    # Local file path (SQLite mode) vs remote signed URL (Supabase mode)
    if os.path.exists(str(url)):
        if is_image:
            st.image(url, width="stretch")
        with open(url, "rb") as f:
            st.download_button("Download", f.read(), file_name=os.path.basename(path))
    else:
        if is_image:
            st.image(url, width="stretch")
        st.link_button("Open bill", url, width="stretch")
