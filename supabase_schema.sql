-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Suppliers Table
create table suppliers (
  id uuid default uuid_generate_v4() primary key,
  name text not null,
  telegram_id bigint,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Products Table
create table products (
  id uuid default uuid_generate_v4() primary key,
  name text not null,
  description text,
  price numeric not null,
  type text not null check (type in ('student', 'trial', 'shared', 'key')),
  fulfillment_type text default 'auto' check (fulfillment_type in ('auto', 'manual')),
  instructions text, -- AI Context
  supplier_id uuid references suppliers(id),
  warranty_days int default 1, -- Гарантия в днях (триалы: 1 день, годовые: 14 дней). Настраивается админом при создании товара
  terms text,
  duration_days int, -- Срок действия в днях (если срок считается от момента покупки)
  status text default 'active' check (status in ('active', 'out_of_stock', 'discontinued', 'coming_soon')),
  status_reason text, -- e.g. "Waiting for Vol 2"
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Stock Items Table
create table stock_items (
  id uuid default uuid_generate_v4() primary key,
  product_id uuid references products(id) not null,
  content text not null,
  expires_at timestamp with time zone,
  is_sold boolean default false,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Users Table
create table users (
  id uuid default uuid_generate_v4() primary key,
  telegram_id bigint unique not null,
  username text,
  first_name text,
  personal_ref_percent int default 20,
  referrer_id uuid references users(id),
  balance numeric default 0,
  is_admin boolean default false,
  do_not_disturb boolean default false,
  is_banned boolean default false,
  warnings_count int default 0,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Orders Table
create table orders (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references users(id) not null,
  product_id uuid references products(id) not null,
  stock_item_id uuid references stock_items(id),
  amount numeric not null,
  original_price numeric, -- Исходная цена товара
  discount_percent numeric default 0, -- Примененная скидка (рассчитывается динамически на основе простоя)
  status text default 'pending', -- pending, paid, refunded, replaced
  payment_method text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  expires_at timestamp with time zone
);

-- Tickets Table (Replacements/Support)
create table tickets (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references users(id) not null,
  order_id uuid references orders(id),
  status text default 'open' check (status in ('open', 'approved', 'rejected', 'closed')),
  issue_type text,
  description text,
  admin_comment text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Waitlist Table
create table waitlist (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references users(id) not null,
  product_name text not null, -- Store name in case product doesn't exist yet
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Analytics Events
create table analytics_events (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references users(id),
  event_type text not null, -- view, checkout, pay, review
  metadata jsonb,
  timestamp timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Chat History
create table chat_history (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references users(id) not null,
  role text not null check (role in ('user', 'assistant')),
  message text not null,
  timestamp timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies
alter table products enable row level security;
create policy "Public products are viewable by everyone" on products for select using (true);

alter table users enable row level security;
create policy "Users can view own data" on users for select using (auth.uid() = id);
