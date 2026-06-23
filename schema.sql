-- Farm Tracker database schema for Supabase (Postgres).
-- Run this once in your Supabase project: SQL Editor -> New query -> paste -> Run.

create table if not exists crops (
    id bigint generated always as identity primary key,
    name text not null,
    season text,
    farm_size_acres numeric default 0,
    start_date date,
    expected_harvest_date date,
    status text default 'Active',
    notes text,
    created_by text,
    created_at timestamptz default now()
);

create table if not exists expenses (
    id bigint generated always as identity primary key,
    date date,
    category text,
    description text,
    vendor text,
    quantity numeric,
    unit text,
    unit_price numeric,
    amount numeric default 0,
    crop_id bigint references crops(id) on delete set null,
    bill_path text,
    created_by text,
    created_at timestamptz default now()
);

create table if not exists harvests (
    id bigint generated always as identity primary key,
    date date,
    crop_id bigint references crops(id) on delete set null,
    quantity_quintal numeric default 0,
    rate_per_quintal numeric default 0,
    amount numeric default 0,
    buyer text,
    transported_quintal numeric default 0,
    transport_cost numeric default 0,
    notes text,
    created_by text,
    created_at timestamptz default now()
);

create table if not exists lifecycle (
    id bigint generated always as identity primary key,
    crop_id bigint references crops(id) on delete cascade,
    stage text,
    planned_date date,
    done_date date,
    status text default 'Pending',
    notes text,
    created_by text,
    created_at timestamptz default now()
);

-- Storage bucket for uploaded bills/receipts.
insert into storage.buckets (id, name, public)
values ('bills', 'bills', false)
on conflict (id) do nothing;
