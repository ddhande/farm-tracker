# 🌾 Farm Tracker

A simple web app to **document farm expenses, harvest, yield and profit** — built for
you and your partner to share. Both of you log in separately, add entries, upload bills,
and instantly see each other's updates.

## What it does

- **Expenses** — record every cost (seed, fertilizer, diesel, labour, transport…) and
  **upload the bill/receipt** (photo or PDF).
- **Harvest & Yield** — record quantity (quintals), rate per quintal, how much was
  transported, transport cost and revenue.
- **Crops & Seasons** — define each crop with its **farm size (acres)** and dates.
- **Crop Lifecycle (SOP)** — a step-by-step checklist from land prep → sowing →
  harvesting → sale, so you can track what's done.
- **Dashboard** — total invested, total revenue, **net profit**, profit margin, yield,
  per-acre figures, and a profit/loss breakdown per crop, with charts.
- **Separate logins** — every entry records who added it.

> Planned next step (not built yet): AI module to pull weather & soil data and flag
> risks to growth/yield. The app is structured so this can be added later.

---

## Option A — Try it on your computer (no setup)

```bash
pip install -r requirements.txt        # or use a virtual environment
streamlit run app.py
```

It opens in your browser. With no configuration it runs in **local mode**: data is
saved in a file `agri_local.db` on your computer, and you can log in with the demo
accounts **darshan / farm123** or **kunal / farm123**.

Local mode is just for trying it out — the data is not shared. To share with your
partner online, follow Option B.

---

## Option B — Deploy free & get a shareable URL (recommended)

This uses three free services. Total time ~15 minutes. You only do this once.

### Step 1 — Put the code on GitHub
1. Create a free account at https://github.com
2. Click **New repository** → name it `farm-tracker` → **Create**.
3. Upload all the files in this folder (drag-and-drop on GitHub's "uploading an
   existing file" page works). **Do not upload** `.streamlit/secrets.toml`,
   `agri_local.db`, or the `uploads/` or `.venv/` folders (the `.gitignore` already
   excludes them).

### Step 2 — Create the shared database (Supabase)
1. Create a free account at https://supabase.com → **New project**.
   Pick any name and a database password (save it somewhere).
2. When the project is ready, open **SQL Editor** → **New query**.
3. Open the file `schema.sql` from this project, copy everything, paste it in,
   and click **Run**. This creates the tables and the `bills` storage bucket.
4. Go to **Project Settings → API** and copy two values:
   - **Project URL** (looks like `https://abcd1234.supabase.co`)
   - **service_role** key (under "Project API keys" — click reveal)

### Step 3 — Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io and sign in **with your GitHub account**.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Choose your `farm-tracker` repo, branch `main`, main file `app.py`.
4. Click **Advanced settings → Secrets** and paste the following (fill in your
   real values from Step 2, and set passwords for each person):

   ```toml
   [supabase]
   url = "https://YOUR-PROJECT.supabase.co"
   key = "YOUR-SERVICE-ROLE-KEY"

   [[auth.users]]
   username = "darshan"
   name = "Darshan"
   password = "pick-a-strong-password"

   [[auth.users]]
   username = "kunal"
   name = "Kunal"
   password = "pick-a-strong-password"
   ```
5. Click **Deploy**. After a minute you'll get a URL like
   `https://farm-tracker.streamlit.app`.

### Step 4 — Share it
Send the URL to your partner along with their username and password. You both
log in separately; everything you each add is saved to the shared Supabase
database and visible to both of you. The sidebar shows **🟢 Shared mode** when
it's connected to Supabase.

---

## Adding or changing logins
Edit the `[[auth.users]]` blocks in your Streamlit Cloud **Secrets** (App →
Settings → Secrets). Add one block per person. Save — the app restarts itself.

## A note on security
`secrets.toml` (with passwords and the Supabase key) is kept only on the server
and is never committed to GitHub or sent to the browser. Keep your GitHub repo's
secrets out of the code as described above.

## Project structure
```
app.py              # entry point + login + navigation
lib/
  config.py         # categories, units, currency, SOP stages
  auth.py           # individual login
  db.py             # data layer (Supabase in production, SQLite locally)
views/
  dashboard.py      # totals, profit, charts, per-crop P&L
  expenses.py       # add expenses + bill upload
  harvest.py        # harvest / yield / transport
  crops.py          # crops & seasons (farm size)
  lifecycle.py      # crop lifecycle / SOP checklist
  bills.py          # browse uploaded bills
schema.sql          # run once in Supabase
```
