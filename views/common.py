"""Shared helpers used across views."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from lib import db


def crop_lookup() -> dict[int, str]:
    """Map crop id -> a readable label."""
    out: dict[int, str] = {}
    for c in db.list_crops():
        season = f" ({c['season']})" if c.get("season") else ""
        out[c["id"]] = f"{c['name']}{season}"
    return out


def crop_select(label: str, key: str, include_all: bool = False, allow_none: bool = True):
    """Render a crop selectbox. Returns selected crop id, or None."""
    import streamlit as st

    lookup = crop_lookup()
    options: list = []
    if include_all:
        options.append(("__all__", "All crops"))
    if allow_none:
        options.append((None, "— Not linked to a crop —"))
    options.extend([(cid, name) for cid, name in lookup.items()])

    if not options:
        st.info("Add a crop first in the **Crops & Seasons** page.")
        return None

    choice = st.selectbox(
        label,
        options,
        format_func=lambda o: o[1],
        key=key,
    )
    return choice[0]


def to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def expenses_df() -> pd.DataFrame:
    df = pd.DataFrame(db.list_expenses())
    if df.empty:
        return df
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    return df


def harvests_df() -> pd.DataFrame:
    df = pd.DataFrame(db.list_harvests())
    if df.empty:
        return df
    for col in ("amount", "quantity_quintal", "rate_per_quintal", "transported_quintal", "transport_cost"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    return df


def crops_df() -> pd.DataFrame:
    df = pd.DataFrame(db.list_crops())
    if df.empty:
        return df
    df["farm_size_acres"] = pd.to_numeric(df.get("farm_size_acres"), errors="coerce").fillna(0.0)
    return df
