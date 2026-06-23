"""Data access layer.

Two interchangeable backends with an identical API:

* SupabaseBackend  -> used in production (shared Postgres DB + file storage).
                      Active when Supabase credentials are present in secrets.
* SQLiteBackend    -> automatic local fallback so the app runs on your computer
                      with no setup. Data lives in ``agri_local.db`` and uploaded
                      bills in the ``uploads/`` folder.

The rest of the app only calls the module-level helper functions at the bottom
and never needs to know which backend is active.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Secrets helpers
# ---------------------------------------------------------------------------

def _get_secret(section: str, key: str) -> Optional[str]:
    """Read a secret without crashing when no secrets file exists."""
    try:
        return st.secrets[section][key]  # type: ignore[index]
    except Exception:
        return None


def _supabase_configured() -> bool:
    return bool(_get_secret("supabase", "url") and _get_secret("supabase", "key"))


# ---------------------------------------------------------------------------
# Base backend
# ---------------------------------------------------------------------------

TABLES = ("crops", "expenses", "harvests", "lifecycle")


class Backend:
    name = "base"

    def init(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    # crops
    def list_crops(self) -> list[dict]: raise NotImplementedError
    def get_crop(self, crop_id) -> Optional[dict]: raise NotImplementedError
    def add_crop(self, data: dict): raise NotImplementedError
    def update_crop(self, crop_id, data: dict): raise NotImplementedError
    def delete_crop(self, crop_id): raise NotImplementedError

    # expenses
    def list_expenses(self) -> list[dict]: raise NotImplementedError
    def add_expense(self, data: dict): raise NotImplementedError
    def delete_expense(self, expense_id): raise NotImplementedError

    # harvests
    def list_harvests(self) -> list[dict]: raise NotImplementedError
    def add_harvest(self, data: dict): raise NotImplementedError
    def delete_harvest(self, harvest_id): raise NotImplementedError

    # lifecycle
    def list_lifecycle(self, crop_id=None) -> list[dict]: raise NotImplementedError
    def add_stage(self, data: dict): raise NotImplementedError
    def update_stage(self, stage_id, data: dict): raise NotImplementedError
    def delete_stage(self, stage_id): raise NotImplementedError

    # bills (file storage)
    def upload_bill(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        raise NotImplementedError

    def bill_url(self, path: str) -> Optional[str]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# SQLite backend (local fallback)
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.getcwd(), "agri_local.db")
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")


class SQLiteBackend(Backend):
    name = "local (SQLite)"

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init(self) -> None:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS crops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    season TEXT,
                    farm_size_acres REAL DEFAULT 0,
                    start_date TEXT,
                    expected_harvest_date TEXT,
                    status TEXT DEFAULT 'Active',
                    notes TEXT,
                    created_by TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    category TEXT,
                    description TEXT,
                    vendor TEXT,
                    quantity REAL,
                    unit TEXT,
                    unit_price REAL,
                    amount REAL DEFAULT 0,
                    crop_id INTEGER,
                    bill_path TEXT,
                    created_by TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS harvests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    crop_id INTEGER,
                    quantity_quintal REAL DEFAULT 0,
                    rate_per_quintal REAL DEFAULT 0,
                    amount REAL DEFAULT 0,
                    buyer TEXT,
                    transported_quintal REAL DEFAULT 0,
                    transport_cost REAL DEFAULT 0,
                    notes TEXT,
                    created_by TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS lifecycle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crop_id INTEGER,
                    stage TEXT,
                    planned_date TEXT,
                    done_date TEXT,
                    status TEXT DEFAULT 'Pending',
                    notes TEXT,
                    created_by TEXT,
                    created_at TEXT
                );
                """
            )

    # --- generic helpers ---
    def _insert(self, table: str, data: dict):
        data = {**data, "created_at": _now()}
        cols = ", ".join(data.keys())
        ph = ", ".join(["?"] * len(data))
        with self._conn() as c:
            cur = c.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", list(data.values()))
            return cur.lastrowid

    def _update(self, table: str, row_id, data: dict):
        if not data:
            return
        sets = ", ".join(f"{k} = ?" for k in data)
        with self._conn() as c:
            c.execute(f"UPDATE {table} SET {sets} WHERE id = ?", [*data.values(), row_id])

    def _delete(self, table: str, row_id):
        with self._conn() as c:
            c.execute(f"DELETE FROM {table} WHERE id = ?", [row_id])

    def _rows(self, sql: str, params=()) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    # crops
    def list_crops(self):
        return self._rows("SELECT * FROM crops ORDER BY created_at DESC")

    def get_crop(self, crop_id):
        rows = self._rows("SELECT * FROM crops WHERE id = ?", [crop_id])
        return rows[0] if rows else None

    def add_crop(self, data):
        return self._insert("crops", data)

    def update_crop(self, crop_id, data):
        self._update("crops", crop_id, data)

    def delete_crop(self, crop_id):
        self._delete("crops", crop_id)

    # expenses
    def list_expenses(self):
        return self._rows("SELECT * FROM expenses ORDER BY date DESC, id DESC")

    def add_expense(self, data):
        return self._insert("expenses", data)

    def delete_expense(self, expense_id):
        self._delete("expenses", expense_id)

    # harvests
    def list_harvests(self):
        return self._rows("SELECT * FROM harvests ORDER BY date DESC, id DESC")

    def add_harvest(self, data):
        return self._insert("harvests", data)

    def delete_harvest(self, harvest_id):
        self._delete("harvests", harvest_id)

    # lifecycle
    def list_lifecycle(self, crop_id=None):
        if crop_id is None:
            return self._rows("SELECT * FROM lifecycle ORDER BY planned_date, id")
        return self._rows(
            "SELECT * FROM lifecycle WHERE crop_id = ? ORDER BY planned_date, id", [crop_id]
        )

    def add_stage(self, data):
        return self._insert("lifecycle", data)

    def update_stage(self, stage_id, data):
        self._update("lifecycle", stage_id, data)

    def delete_stage(self, stage_id):
        self._delete("lifecycle", stage_id)

    # bills
    def upload_bill(self, file_bytes, filename, content_type):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe = f"{uuid.uuid4().hex}_{filename}".replace("/", "_")
        with open(os.path.join(UPLOAD_DIR, safe), "wb") as f:
            f.write(file_bytes)
        return safe

    def bill_url(self, path):
        if not path:
            return None
        full = os.path.join(UPLOAD_DIR, path)
        return full if os.path.exists(full) else None


# ---------------------------------------------------------------------------
# Supabase backend (production)
# ---------------------------------------------------------------------------

BUCKET = "bills"


class SupabaseBackend(Backend):
    name = "Supabase (shared)"

    def __init__(self):
        from supabase import create_client

        self.client = create_client(
            _get_secret("supabase", "url"),
            _get_secret("supabase", "key"),
        )

    def init(self) -> None:
        # Tables and the storage bucket are created once via schema.sql in the
        # Supabase dashboard (see README). Nothing to do at runtime.
        return None

    def _table(self, name):
        return self.client.table(name)

    # crops
    def list_crops(self):
        return self._table("crops").select("*").order("created_at", desc=True).execute().data or []

    def get_crop(self, crop_id):
        data = self._table("crops").select("*").eq("id", crop_id).execute().data
        return data[0] if data else None

    def add_crop(self, data):
        res = self._table("crops").insert(data).execute()
        return res.data[0]["id"] if res.data else None

    def update_crop(self, crop_id, data):
        self._table("crops").update(data).eq("id", crop_id).execute()

    def delete_crop(self, crop_id):
        self._table("crops").delete().eq("id", crop_id).execute()

    # expenses
    def list_expenses(self):
        return (
            self._table("expenses").select("*").order("date", desc=True).execute().data or []
        )

    def add_expense(self, data):
        res = self._table("expenses").insert(data).execute()
        return res.data[0]["id"] if res.data else None

    def delete_expense(self, expense_id):
        self._table("expenses").delete().eq("id", expense_id).execute()

    # harvests
    def list_harvests(self):
        return (
            self._table("harvests").select("*").order("date", desc=True).execute().data or []
        )

    def add_harvest(self, data):
        res = self._table("harvests").insert(data).execute()
        return res.data[0]["id"] if res.data else None

    def delete_harvest(self, harvest_id):
        self._table("harvests").delete().eq("id", harvest_id).execute()

    # lifecycle
    def list_lifecycle(self, crop_id=None):
        q = self._table("lifecycle").select("*").order("planned_date")
        if crop_id is not None:
            q = q.eq("crop_id", crop_id)
        return q.execute().data or []

    def add_stage(self, data):
        res = self._table("lifecycle").insert(data).execute()
        return res.data[0]["id"] if res.data else None

    def update_stage(self, stage_id, data):
        self._table("lifecycle").update(data).eq("id", stage_id).execute()

    def delete_stage(self, stage_id):
        self._table("lifecycle").delete().eq("id", stage_id).execute()

    # bills
    def upload_bill(self, file_bytes, filename, content_type):
        path = f"{uuid.uuid4().hex}_{filename}".replace("/", "_")
        self.client.storage.from_(BUCKET).upload(
            path,
            file_bytes,
            {"content-type": content_type or "application/octet-stream", "upsert": "true"},
        )
        return path

    def bill_url(self, path):
        if not path:
            return None
        try:
            res = self.client.storage.from_(BUCKET).create_signed_url(path, 3600)
            return res.get("signedURL") or res.get("signedUrl")
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Backend selection + public module API
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@st.cache_resource(show_spinner=False)
def get_backend() -> Backend:
    if _supabase_configured():
        try:
            backend: Backend = SupabaseBackend()
        except Exception as exc:  # fall back gracefully
            st.warning(f"Could not connect to Supabase ({exc}). Using local storage instead.")
            backend = SQLiteBackend()
    else:
        backend = SQLiteBackend()
    backend.init()
    return backend


def init() -> None:
    """Ensure the active backend is ready (tables created for SQLite)."""
    get_backend()


def backend_name() -> str:
    return get_backend().name


def is_shared() -> bool:
    return _supabase_configured()


# crops
def list_crops():
    return get_backend().list_crops()

def get_crop(crop_id):
    return get_backend().get_crop(crop_id)

def add_crop(data):
    return get_backend().add_crop(data)

def update_crop(crop_id, data):
    return get_backend().update_crop(crop_id, data)

def delete_crop(crop_id):
    return get_backend().delete_crop(crop_id)


# expenses
def list_expenses():
    return get_backend().list_expenses()

def add_expense(data):
    return get_backend().add_expense(data)

def delete_expense(expense_id):
    return get_backend().delete_expense(expense_id)


# harvests
def list_harvests():
    return get_backend().list_harvests()

def add_harvest(data):
    return get_backend().add_harvest(data)

def delete_harvest(harvest_id):
    return get_backend().delete_harvest(harvest_id)


# lifecycle
def list_lifecycle(crop_id=None):
    return get_backend().list_lifecycle(crop_id)

def add_stage(data):
    return get_backend().add_stage(data)

def update_stage(stage_id, data):
    return get_backend().update_stage(stage_id, data)

def delete_stage(stage_id):
    return get_backend().delete_stage(stage_id)


# bills
def upload_bill(file_bytes, filename, content_type):
    return get_backend().upload_bill(file_bytes, filename, content_type)

def bill_url(path):
    return get_backend().bill_url(path)
