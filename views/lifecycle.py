"""Crop Lifecycle / SOP: track each stage of the crop from sowing to sale."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from lib import config, db
from lib.auth import can_modify, current_username
from views.common import crop_lookup


def render() -> None:
    st.header("📅 Crop Lifecycle (SOP)")
    st.caption("Plan and track every stage of the crop — what's done and what's pending.")

    lookup = crop_lookup()
    if not lookup:
        st.info("Add a crop first in the **Crops & Seasons** page.")
        return

    crop_id = st.selectbox(
        "Select crop",
        list(lookup.keys()),
        format_func=lambda i: lookup[i],
        key="lc_crop",
    )

    stages = db.list_lifecycle(crop_id)

    if not stages:
        st.info("No stages yet for this crop.")
        if st.button("📋 Load standard SOP stages", type="primary"):
            for s in config.LIFECYCLE_STAGES:
                db.add_stage(
                    {
                        "crop_id": crop_id,
                        "stage": s,
                        "planned_date": None,
                        "done_date": None,
                        "status": "Pending",
                        "notes": "",
                        "created_by": current_username(),
                    }
                )
            st.rerun()

    if stages:
        done = sum(1 for s in stages if s.get("status") == "Done")
        st.progress(done / len(stages), text=f"{done} of {len(stages)} stages done")

        df = pd.DataFrame(stages)[["stage", "status", "planned_date", "done_date", "notes"]]
        df = df.rename(
            columns={
                "stage": "Stage",
                "status": "Status",
                "planned_date": "Planned",
                "done_date": "Done on",
                "notes": "Notes",
            }
        )
        st.dataframe(df, width="stretch", hide_index=True)

        with st.expander("✏️ Update a stage"):
            editable = [s for s in stages if can_modify(s)]
            if not editable:
                st.caption("You can only update or delete stages you added yourself.")
                pick = None
            else:
                pick = st.selectbox(
                    "Stage",
                    editable,
                    format_func=lambda s: f"{s['stage']} ({s.get('status')})",
                    key="lc_stage_pick",
                )
            if pick:
                with st.form("update_stage"):
                    c1, c2 = st.columns(2)
                    with c1:
                        status = st.selectbox(
                            "Status",
                            config.STAGE_STATUSES,
                            index=config.STAGE_STATUSES.index(pick["status"])
                            if pick.get("status") in config.STAGE_STATUSES
                            else 0,
                        )
                        planned = st.date_input(
                            "Planned date",
                            value=_parse_date(pick.get("planned_date")),
                        )
                    with c2:
                        done_on = st.date_input(
                            "Done on",
                            value=_parse_date(pick.get("done_date")),
                        )
                        mark_done_today = st.checkbox("Mark done today")
                    notes = st.text_area("Notes", value=pick.get("notes") or "")
                    cc1, cc2 = st.columns(2)
                    save = cc1.form_submit_button("Save", type="primary")
                    remove = cc2.form_submit_button("Delete stage")
                if save:
                    done_value = str(date.today()) if mark_done_today else str(done_on)
                    db.update_stage(
                        pick["id"],
                        {
                            "status": "Done" if mark_done_today else status,
                            "planned_date": str(planned),
                            "done_date": done_value,
                            "notes": notes.strip(),
                        },
                    )
                    st.success("Stage updated.")
                    st.rerun()
                if remove:
                    db.delete_stage(pick["id"])
                    st.warning("Stage deleted.")
                    st.rerun()

    with st.expander("➕ Add a custom stage"):
        with st.form("add_stage", clear_on_submit=True):
            name = st.text_input("Stage name")
            c1, c2 = st.columns(2)
            planned = c1.date_input("Planned date", value=date.today())
            status = c2.selectbox("Status", config.STAGE_STATUSES)
            notes = st.text_area("Notes", key="add_stage_notes")
            submitted = st.form_submit_button("Add stage", type="primary")
        if submitted:
            if not name.strip():
                st.error("Stage name is required.")
            else:
                db.add_stage(
                    {
                        "crop_id": crop_id,
                        "stage": name.strip(),
                        "planned_date": str(planned),
                        "done_date": None,
                        "status": status,
                        "notes": notes.strip(),
                        "created_by": current_username(),
                    }
                )
                st.success("Stage added.")
                st.rerun()


def _parse_date(value):
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return date.today()
