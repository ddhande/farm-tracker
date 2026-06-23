"""Expenses: record every cost and attach a bill/receipt."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from lib import config, db
from lib.auth import can_modify, current_username
from views.common import crop_lookup, crop_select, expenses_df


def render() -> None:
    st.header("🧾 Expenses")
    st.caption("Log every purchase (seed, fertilizer, diesel, labour…) and upload the bill.")

    with st.expander("➕ Add an expense", expanded=True):
        with st.form("add_expense", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                e_date = st.date_input("Date", value=date.today())
                category = st.selectbox("Category", config.EXPENSE_CATEGORIES)
                vendor = st.text_input("Vendor / shop", placeholder="Who you paid")
            with c2:
                quantity = st.number_input("Quantity", min_value=0.0, step=1.0, value=0.0)
                unit = st.selectbox("Unit", config.PURCHASE_UNITS)
                unit_price = st.number_input(
                    f"Rate per unit ({config.CURRENCY})", min_value=0.0, step=1.0, value=0.0
                )
            with c3:
                amount = st.number_input(
                    f"Total amount ({config.CURRENCY})",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    help="Leave 0 to auto-calculate as Quantity × Rate.",
                )
                crop_id = crop_select("Link to crop (optional)", key="exp_crop")
            description = st.text_input("Description", placeholder="e.g. Urea 50kg bags")
            bill = st.file_uploader(
                "Upload bill / receipt (optional)",
                type=["png", "jpg", "jpeg", "pdf", "webp"],
            )
            submitted = st.form_submit_button("Add expense", type="primary")

        if submitted:
            final_amount = amount if amount > 0 else quantity * unit_price
            if final_amount <= 0:
                st.error("Enter a total amount, or both quantity and rate per unit.")
            else:
                bill_path = None
                if bill is not None:
                    try:
                        bill_path = db.upload_bill(bill.getvalue(), bill.name, bill.type)
                    except Exception as exc:
                        st.warning(f"Expense saved, but bill upload failed: {exc}")
                db.add_expense(
                    {
                        "date": str(e_date),
                        "category": category,
                        "description": description.strip(),
                        "vendor": vendor.strip(),
                        "quantity": float(quantity),
                        "unit": unit,
                        "unit_price": float(unit_price),
                        "amount": float(final_amount),
                        "crop_id": crop_id,
                        "bill_path": bill_path,
                        "created_by": current_username(),
                    }
                )
                st.success(f"Added expense of {config.money(final_amount)}.")
                st.rerun()

    df = expenses_df()
    if df.empty:
        st.info("No expenses recorded yet.")
        return

    lookup = crop_lookup()

    st.subheader("Recorded expenses")
    f1, f2 = st.columns(2)
    cat_filter = f1.multiselect("Filter by category", config.EXPENSE_CATEGORIES)
    crop_names = ["All"] + list(lookup.values())
    crop_filter = f2.selectbox("Filter by crop", crop_names)

    view = df.copy()
    if cat_filter:
        view = view[view["category"].isin(cat_filter)]
    if crop_filter != "All":
        target_id = next((cid for cid, n in lookup.items() if n == crop_filter), None)
        view = view[view["crop_id"] == target_id]

    view = view.assign(
        Crop=view["crop_id"].map(lambda i: lookup.get(i, "—")),
        Bill=view["bill_path"].map(lambda p: "📎" if p else ""),
    )
    table = view[
        ["date", "category", "description", "vendor", "quantity", "unit", "unit_price", "amount", "Crop", "Bill", "created_by"]
    ].rename(
        columns={
            "date": "Date",
            "category": "Category",
            "description": "Description",
            "vendor": "Vendor",
            "quantity": "Qty",
            "unit": "Unit",
            "unit_price": f"Rate ({config.CURRENCY})",
            "amount": f"Amount ({config.CURRENCY})",
            "created_by": "Added by",
        }
    )
    st.dataframe(table, width="stretch", hide_index=True)

    total = view["amount"].sum()
    m1, m2 = st.columns(2)
    m1.metric("Total (filtered)", config.money(total))
    m2.metric("Entries", len(view))

    with st.expander("🗑️ Delete an expense"):
        records = [r for r in db.list_expenses() if can_modify(r)]
        if not records:
            st.caption("You can only delete expenses you added yourself.")
        else:
            pick = st.selectbox(
                "Select expense to delete",
                records,
                format_func=lambda r: f"{r['date']} · {r['category']} · {config.money(r['amount'])} · {r.get('description') or ''}",
                key="del_expense_pick",
            )
            if st.button("Delete selected expense"):
                db.delete_expense(pick["id"])
                st.warning("Expense deleted.")
                st.rerun()
