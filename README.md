# Haldiram

Food ordering for Haldiram: members register with name, phone and password; customers browse the menu, build a cart, and check out choosing delivery / pickup / table dining plus cash on delivery, UPI or pay-at-counter. My Orders tracks each order's status; the owner advances orders placed → preparing → ready → completed and checks UPI payments from the dashboard and queue.

Built by its owner on [DoneJi](https://doneji.app) — the AI drafted it, the owner read every file and passed an explain-it-back exam on the code before it could ship.

## Run it locally

1. Set DATABASE_URL, SECRET_KEY (and UPI_VPA to enable UPI) in the environment
2. python app.py — schema.sql creates the tables and seeds the Haldiram menu
3. Register an owner account, then a customer account and place an order

## Deployment

- **App**: Vercel, auto-deploys on every push to `main`
- **Database**: Supabase; the schema lives in `supabase/migrations/` and applies automatically on push
