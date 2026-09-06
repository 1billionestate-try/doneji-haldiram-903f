-- Initial schema for Haldiram.
-- Lives under supabase/migrations/ so that Supabase's GitHub integration
-- applies it automatically on every push to main. To change the schema
-- later, add a NEW file with a newer timestamp — never edit this one:
-- applied migrations are tracked by timestamp and an edited file is
-- silently skipped.

-- Haldiram: four tables, because an order is not one thing — who ordered,
-- what is on the menu, the order itself, and the LINES inside it.

create table if not exists users (
  id            serial primary key,
  name          text not null,
  -- Every member is identified by their phone number — it is their
  -- username at the counter, so it must be unique.
  phone         text not null unique,
  email         text unique,
  password_hash text not null,
  -- 'owner' manages items and the queue; 'customer' browses and orders.
  role          text not null default 'customer' constraint users_role_check check (role in ('owner', 'customer'))
);

create table if not exists items (
  id           serial primary key,
  name         text          not null unique,
  category     text          not null,          -- e.g. 'Snacks', 'Sweets'
  price        numeric(7,2)  not null constraint items_price_check check (price >= 0),
  is_available boolean       not null default true,
  -- A direct https image link the owner pastes in the menu editor. NULL means
  -- the menu shows a neutral placeholder photo instead.
  image_url    text
);

create table if not exists orders (
  id         serial primary key,
  user_id    integer not null references users(id) on delete cascade,
  status     text    not null default 'placed'
             constraint orders_status_check check (status in ('placed', 'preparing', 'ready', 'completed')),
  -- HOW the customer wants the food, chosen at checkout. The three detail
  -- columns are one-per-mode and nullable; the one matching the chosen mode
  -- is required BY PYTHON in place_order — a cross-column CHECK here plus
  -- request.form.get(..., "") once killed every dine-in order ('' is not
  -- NULL), so the database keeps single-column, named constraints only.
  fulfillment text   not null default 'pickup'
             constraint orders_fulfillment_check check (fulfillment in ('delivery', 'pickup', 'table')),
  address     text,
  pickup_time text,  -- text on purpose: "6:30 pm" broke a timestamp column once
  table_no    integer constraint orders_table_no_check check (table_no > 0),
  -- HOW the customer chose to pay: NULL until they answer the question on the
  -- order-placed page. Whether money actually arrived lives in payments —
  -- the choice and the fact are two different things.
  pay_method text    constraint orders_pay_method_check check (pay_method in ('upi', 'counter')),
  placed_at  timestamp not null default now()
);

create table if not exists order_items (
  id             serial primary key,
  order_id       integer      not null references orders(id) on delete cascade,
  item_id        integer      not null references items(id) on delete cascade,
  qty            integer      not null constraint order_items_qty_check check (qty > 0),
  -- The price is COPIED here on purpose. The menu price changes tomorrow;
  -- the bill for an order already placed must never change with it.
  price_at_order numeric(7,2) not null
);

-- Sample Haldiram menu so the app is usable on first run. ON CONFLICT makes
-- this safe to run every start: an existing name is simply left alone.
insert into items (name, category, price) values
  ('Samosa',               'Snacks', 30),
  ('Kachori',              'Snacks', 25),
  ('Dhokla',               'Snacks', 45),
  ('Kaju Katli 500g box',  'Sweets', 450),
  ('Rasmalai',             'Sweets', 80),
  ('Gulab Jamun (2 pc)',   'Sweets', 60),
  ('Motichoor Ladoo 500g', 'Sweets', 320),
  ('Raj Kachori',          'Chaat',  90),
  ('Pav Bhaji',            'Meals',  110),
  ('Masala Chai',          'Drinks', 20)
on conflict (name) do nothing;

-- One payment per thing being paid for. The columns split deliberately down
-- the middle: what the CUSTOMER says happened, and what the OWNER confirmed
-- after looking at their own bank app. Never collapse them into one "paid"
-- flag — a claim is not a confirmation.
create table if not exists payments (
  id          serial primary key,
  -- Which row is being paid for. 'order' here. There is deliberately no
  -- FOREIGN KEY: one table serves different parent shapes.
  target_kind text not null,
  target_id   integer not null,
  amount      numeric(10,2) not null constraint payments_amount_check check (amount > 0),
  status      text not null default 'awaiting'
              constraint payments_status_check check (status in ('awaiting', 'claimed', 'verified', 'rejected')),

  -- What the customer typed. Never trusted: a UPI reference is 12 digits and
  -- anyone can type 12 digits. The CHECK is shape, not proof.
  claimed_ref text constraint payments_claimed_ref_check check (claimed_ref ~ '^[0-9]{12}$'),
  claimed_by  integer references users(id) on delete set null,
  claimed_at  timestamp,

  -- What the owner confirmed, by eye, against their own UPI app.
  verified_by integer references users(id) on delete set null,
  verified_at timestamp,

  note        text not null default '',
  -- One payment row per thing. This is what makes the insert idempotent, so
  -- opening the pay panel twice cannot create two rows.
  unique (target_kind, target_id)
);
