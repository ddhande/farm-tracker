"""Harvest & Yield: record produce, rate per quintal, transport and revenue."""

from __future__ import annotations

from datetime import date

import streamlit as st

from lib import config, db
from lib.auth import can_modify, current_username
from views.common import crop_lookup, crop_select, harvests_df


def render() -> None:
    st.header("🌾 Harvest & Yield")
    st.caption("Record how much you harvested, the selling rate, and how much was transported.")

    with st.expander("➕ Add a harvest / sale record", expanded=True):
        with st.form("add_harvest", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                h_date = st.date_input("Date", value=date.today())
                crop_id = crop_select("Crop", key="harv_crop", allow_none=True)
                buyer = st.text_input("Buyer / market", placeholder="e.g. APMC mandi")
            with c2:
                quantity = st.number_input(
                    f"Yield ({config.YIELD_UNIT})", min_value=0.0, step=0.5, value=0.0
                )
                rate = st.number_input(
                    f"Rate per {config.YIELD_UNIT} ({config.CURRENCY})",
                    min_value=0.0,
                    step=10.0,
                    value=0.0,
                )
            with c3:
                transported = st.number_input(
                    f"Transported ({config.YIELD_UNIT})", min_value=0.0, step=0.5, value=0.0
                )
                transport_cost = st.number_input(
                    f"Transport cost ({config.CURRENCY})", min_value=0.0, step=10.0, value=0.0
                )
            notes = st.text_area("Notes", placeholder="Quality, vehicle, deductions, etc.")
            submitted = st.form_submit_button("Add harvest record", type="primary")

        if submitted:
            amount = quantity * rate
            if quantity <= 0:
                st.error("Enter the yield quantity.")
            else:
                db.add_harvest(
                    {
                        "date": str(h_date),
                        "crop_id": crop_id,
                        "quantity_quintal": float(quantity),
                        "rate_per_quintal": float(rate),
                        "amount": float(amount),
                        "buyer": buyer.strip(),
                        "transported_quintal": float(transported),
                        "transport_cost": float(transport_cost),
                        "notes": notes.strip(),
                        "created_by": current_username(),
                    }
                )
                st.success(f"Added harvest: {quantity} {config.YIELD_UNIT} → {config.money(amount)}.")
                st.rerun()

    df = harvests_df()
    if df.empty:
        st.info("No harvest records yet.")
        return

    lookup = crop_lookup()
    view = df.assign(Crop=df["crop_id"].map(lambda i: lookup.get(i, "—")))

    st.subheader("Harvest records")
    table = view[
        ["date", "Crop", "quantity_quintal", "rate_per_quintal", "amount", "transported_quintal", "transport_cost", "buyer", "created_by"]
    ].rename(
        columns={
            "date": "Date",
            "quantity_quintal": f"Yield ({config.YIELD_UNIT})",
            "rate_per_quintal": f"Rate ({config.CURRENCY})",
            "amount": f"Revenue ({config.CURRENCY})",
            "transported_quintal": f"Transported ({config.YIELD_UNIT})",
            "transport_cost": f"Transport ({config.CURRENCY})",
            "buyer": "Buyer",
            "created_by": "Added by",
        }
    )
    st.dataframe(table, width="stretch", hide_index=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Total yield ({config.YIELD_UNIT})", f"{df['quantity_quintal'].sum():,.2f}")
    m2.metric("Total revenue", config.money(df["amount"].sum()))
    m3.metric(f"Total transported ({config.YIELD_UNIT})", f"{df['transported_quintal'].sum():,.2f}")
    m4.metric("Total transport cost", config.money(df["transport_cost"].sum()))

    with st.expander("🗑️ Delete a harvest record"):
        records = [r for r in db.list_harvests() if can_modify(r)]
        if not records:
            st.caption("You can only delete harvest records you added yourself.")
        else:
            pick = st.selectbox(
                "Select record to delete",
                records,
                format_func=lambda r: f"{r['date']} · {lookup.get(r.get('crop_id'), '—')} · {r['quantity_quintal']} {config.YIELD_UNIT} · {config.money(r['amount'])}",
                key="del_harvest_pick",
            )
            if st.button("Delete selected record"):
                db.delete_harvest(pick["id"])
                st.warning("Record deleted.")
                st.rerun()
