"""Crops & Seasons: define each crop/season and its farm size."""

from __future__ import annotations

from datetime import date

import streamlit as st

from lib import config, db
from lib.auth import current_username
from views.common import crops_df


def render() -> None:
    st.header("🌱 Crops & Seasons")
    st.caption("Create a crop/season here first, then link expenses, harvest and SOP stages to it.")

    with st.expander("➕ Add a new crop / season", expanded=not db.list_crops()):
        with st.form("add_crop", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Crop name *", placeholder="e.g. Cotton, Wheat, Tomato")
                season = st.text_input("Season / year", placeholder="e.g. Kharif 2026")
                farm_size = st.number_input(
                    f"Farm size ({config.AREA_UNIT})", min_value=0.0, step=0.5, value=0.0
                )
            with col2:
                start = st.date_input("Sowing / start date", value=date.today())
                harvest = st.date_input("Expected harvest date", value=date.today())
                status = st.selectbox("Status", config.CROP_STATUSES, index=1)
            notes = st.text_area("Notes", placeholder="Variety, field location, etc.")
            submitted = st.form_submit_button("Add crop", type="primary")
        if submitted:
            if not name.strip():
                st.error("Crop name is required.")
            else:
                db.add_crop(
                    {
                        "name": name.strip(),
                        "season": season.strip(),
                        "farm_size_acres": float(farm_size),
                        "start_date": str(start),
                        "expected_harvest_date": str(harvest),
                        "status": status,
                        "notes": notes.strip(),
                        "created_by": current_username(),
                    }
                )
                st.success(f"Added crop “{name}”.")
                st.rerun()

    df = crops_df()
    if df.empty:
        st.info("No crops yet. Add your first crop above.")
        return

    st.subheader("Your crops")
    show = df[
        ["id", "name", "season", "farm_size_acres", "status", "start_date", "expected_harvest_date", "created_by"]
    ].rename(
        columns={
            "farm_size_acres": f"Size ({config.AREA_UNIT})",
            "start_date": "Start",
            "expected_harvest_date": "Exp. harvest",
            "created_by": "Added by",
        }
    )
    st.dataframe(show, width="stretch", hide_index=True)
    st.metric(f"Total farm size ({config.AREA_UNIT})", f"{df['farm_size_acres'].sum():,.2f}")

    with st.expander("✏️ Edit or delete a crop"):
        crops = db.list_crops()
        pick = st.selectbox(
            "Select crop",
            crops,
            format_func=lambda c: f"{c['name']} ({c.get('season') or '—'})",
            key="edit_crop_pick",
        )
        if pick:
            with st.form("edit_crop"):
                c1, c2 = st.columns(2)
                with c1:
                    e_name = st.text_input("Crop name", value=pick.get("name", ""))
                    e_season = st.text_input("Season / year", value=pick.get("season") or "")
                    e_size = st.number_input(
                        f"Farm size ({config.AREA_UNIT})",
                        min_value=0.0,
                        step=0.5,
                        value=float(pick.get("farm_size_acres") or 0),
                    )
                with c2:
                    e_status = st.selectbox(
                        "Status",
                        config.CROP_STATUSES,
                        index=config.CROP_STATUSES.index(pick["status"])
                        if pick.get("status") in config.CROP_STATUSES
                        else 1,
                    )
                    e_notes = st.text_area("Notes", value=pick.get("notes") or "")
                cc1, cc2 = st.columns(2)
                save = cc1.form_submit_button("Save changes", type="primary")
                remove = cc2.form_submit_button("Delete crop")
            if save:
                db.update_crop(
                    pick["id"],
                    {
                        "name": e_name.strip(),
                        "season": e_season.strip(),
                        "farm_size_acres": float(e_size),
                        "status": e_status,
                        "notes": e_notes.strip(),
                    },
                )
                st.success("Crop updated.")
                st.rerun()
            if remove:
                db.delete_crop(pick["id"])
                st.warning("Crop deleted.")
                st.rerun()
