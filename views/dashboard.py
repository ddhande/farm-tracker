"""Dashboard: investment, revenue, profit and yield at a glance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import config
from views.common import crop_lookup, crops_df, expenses_df, harvests_df


def render() -> None:
    st.header("📊 Dashboard")

    exp = expenses_df()
    har = harvests_df()
    crops = crops_df()

    total_invested = float(exp["amount"].sum()) if not exp.empty else 0.0
    total_transport = float(har["transport_cost"].sum()) if not har.empty else 0.0
    total_cost = total_invested  # expenses already include transport entries if logged there
    total_revenue = float(har["amount"].sum()) if not har.empty else 0.0
    total_yield = float(har["quantity_quintal"].sum()) if not har.empty else 0.0
    total_transported = float(har["transported_quintal"].sum()) if not har.empty else 0.0
    profit = total_revenue - total_cost
    farm_size = float(crops["farm_size_acres"].sum()) if not crops.empty else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total invested", config.money(total_cost))
    m2.metric("Total revenue", config.money(total_revenue))
    m3.metric("Net profit", config.money(profit), delta=config.money(profit))
    m4.metric(f"Total yield ({config.YIELD_UNIT})", f"{total_yield:,.2f}")

    n1, n2, n3, n4 = st.columns(4)
    n1.metric(f"Farm size ({config.AREA_UNIT})", f"{farm_size:,.2f}")
    n2.metric(f"Transported ({config.YIELD_UNIT})", f"{total_transported:,.2f}")
    n3.metric("Transport cost", config.money(total_transport))
    margin = (profit / total_revenue * 100) if total_revenue else 0.0
    n4.metric("Profit margin", f"{margin:,.1f}%")

    if farm_size > 0:
        st.markdown(f"##### Per {config.AREA_UNIT} (across {farm_size:,.2f} {config.AREA_UNIT})")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Cost", config.money(total_cost / farm_size))
        p2.metric("Revenue", config.money(total_revenue / farm_size))
        p3.metric("Profit", config.money(profit / farm_size))
        p4.metric(f"Yield ({config.YIELD_UNIT})", f"{total_yield / farm_size:,.2f}")

    st.divider()

    if exp.empty and har.empty:
        st.info("Start by adding crops, expenses and harvest records to see your dashboard.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Expenses by category")
        if not exp.empty:
            by_cat = exp.groupby("category")["amount"].sum().sort_values(ascending=False)
            st.bar_chart(by_cat)
        else:
            st.caption("No expenses yet.")

    with c2:
        st.subheader("Cost vs Revenue vs Profit")
        summary = pd.DataFrame(
            {"Amount": [total_cost, total_revenue, profit]},
            index=["Invested", "Revenue", "Profit"],
        )
        st.bar_chart(summary)

    if not exp.empty:
        st.subheader("Spending over time")
        timeline = exp.dropna(subset=["date"]).copy()
        if not timeline.empty:
            monthly = (
                timeline.set_index("date")["amount"].resample("MS").sum()
            )
            st.line_chart(monthly)

    _per_crop_table(exp, har)


def _per_crop_table(exp: pd.DataFrame, har: pd.DataFrame) -> None:
    lookup = crop_lookup()
    if not lookup:
        return
    st.subheader("Profit & loss by crop")
    rows = []
    for cid, name in lookup.items():
        invested = float(exp[exp["crop_id"] == cid]["amount"].sum()) if not exp.empty else 0.0
        revenue = float(har[har["crop_id"] == cid]["amount"].sum()) if not har.empty else 0.0
        yield_q = (
            float(har[har["crop_id"] == cid]["quantity_quintal"].sum()) if not har.empty else 0.0
        )
        rows.append(
            {
                "Crop": name,
                f"Invested ({config.CURRENCY})": round(invested, 2),
                f"Revenue ({config.CURRENCY})": round(revenue, 2),
                f"Profit ({config.CURRENCY})": round(revenue - invested, 2),
                f"Yield ({config.YIELD_UNIT})": round(yield_q, 2),
            }
        )
    # unlinked
    unl_inv = float(exp[exp["crop_id"].isna()]["amount"].sum()) if not exp.empty else 0.0
    unl_rev = float(har[har["crop_id"].isna()]["amount"].sum()) if not har.empty else 0.0
    if unl_inv or unl_rev:
        rows.append(
            {
                "Crop": "Not linked to a crop",
                f"Invested ({config.CURRENCY})": round(unl_inv, 2),
                f"Revenue ({config.CURRENCY})": round(unl_rev, 2),
                f"Profit ({config.CURRENCY})": round(unl_rev - unl_inv, 2),
                f"Yield ({config.YIELD_UNIT})": 0.0,
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
