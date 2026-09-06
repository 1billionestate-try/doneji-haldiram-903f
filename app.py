"""Every page of the order desk, in plain Python.

Flask is the only non-syllabus piece, and it is small: @app.route("/x") means
"when someone opens /x, run this function". Everything inside the functions
is the Python and SQL from your own course.
"""
import os
from datetime import date

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db
import doneji
import payments
import photos

app = Flask(__name__)
# No fallback on purpose. A default here would quietly become the real
# signing key the day someone forgets to set the variable, and every session
# cookie would then be forgeable by anyone who has read this template.
app.secret_key = os.environ["SECRET_KEY"]

# Real photos for dishes everyone recognises, as a Jinja global so every menu
# page can ask per row. The chain on each card: the owner's own pasted photo,
# else stock_photo(name), else the neutral initial tile.
app.jinja_env.globals["stock_photo"] = photos.stock_photo

# DoneJi's supervision layer: the health ping, the /privacy page, the
# read-only reviewer session and the footer line. One call, so that everything
# it attaches lives in doneji.py where it can be read in one sitting.
doneji.install(app)


@app.route("/.well-known/doneji.txt")
def doneji_proof():
    """Proves this deployment is yours.

    DoneJi issues one random token per project and checks that YOUR site
    serves it back here. Being reachable only shows a site exists; serving a
    secret you were given shows you control it — which is why pasting a
    classmate's URL cannot pass. The token lives in the environment, never in
    the code, for exactly the reason SECRET_KEY does.
    """
    return os.environ.get("DONEJI_VERIFY_TOKEN", ""), 200, {"Content-Type": "text/plain"}


def current_user():
    """The logged-in user's row, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.query_one("select id, name, email, role from users where id = %s", (user_id,))


def cart_lines():
    """The session cart as menu rows with quantities.

    The cart lives in the session cookie as {item_id: qty} — it is not an
    order yet, so it does not belong in the database. Session keys arrive
    back as strings, which is why each id is cast before its lookup.
    """
    cart = session.get("cart", {})
    lines = []
    total = 0
    for item_id, qty in sorted(cart.items()):
        row = db.query_one("select id, name, price from items where id = %s", (int(item_id),))
        if not row:
            continue
        qty = int(qty)
        line_total = qty * row["price"]
        total += line_total
        lines.append({"id": row["id"], "name": row["name"], "qty": qty, "line_total": line_total})
    return lines, total


@app.route("/")
def home():
    """The menu. Browsable without logging in; ordering needs an account."""
    user = current_user()
    category = request.args.get("category", "").strip()
    if category:
        items = db.query(
            "select id, name, category, price, image_url from items where is_available and category = %s order by name",
            (category,),
        )
    else:
        items = db.query(
            "select id, name, category, price, image_url from items where is_available order by category, name"
        )
    categories = db.query(
        "select distinct category from items where is_available order by category"
    )
    lines, total = cart_lines()
    return render_template(
        "home.html", items=items, categories=categories, active=category,
        user=user, cart=lines, cart_total=total,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"].strip()
        user = db.query_one("select id, role, password_hash from users where phone = %s", (phone,))
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            # The owner runs the counter, so the counter is their home page.
            # A customer is here to eat, so they land on the menu.
            if user["role"] == "owner":
                return redirect(url_for("dashboard"))
            return redirect(url_for("home"))
        return render_template("login.html", error="Wrong email or password.")
    return render_template("login.html", error=None)


@app.route("/register", methods=["GET", "POST"])
def register():
    """A new member gives a name, a phone number and a password.

    The phone is the member's identity at the counter, so the users table
    carries a UNIQUE constraint on it and the insert fails loudly on a
    duplicate; we check first so the form can say so politely.
    """
    if request.method == "POST":
        phone = request.form["phone"].strip()
        if not phone.isdigit() or len(phone) != 10:
            return render_template("register.html", error="Please enter a 10-digit phone number.")
        if db.query_one("select id from users where phone = %s", (phone,)):
            return render_template("register.html", error="That phone number is already registered.")
        role = "owner" if request.form.get("role") == "owner" else "customer"
        # row_from_form reads the users table's own column list: name and
        # phone come from the form, everything else is added here.
        row, errors = db.row_from_form(request.form, "users", required=("name", "phone"),
                                       only=("name", "phone"))
        if errors:
            return render_template("register.html", error=errors[0])
        row["phone"] = phone
        row["password_hash"] = generate_password_hash(request.form["password"])
        row["role"] = role
        db.insert_from_form("users", row)
        return redirect(url_for("login"))
    return render_template("register.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


def dashboard_stats():
    """The owner's dashboard, in this app's own words.

    doneji.py owns the /dashboard URL so that it can never be deleted; this
    function owns everything the page says. Return None and the visitor is
    sent away — the permission rule is the app's, not the platform's.
    """
    user = current_user()
    if not user or user["role"] != "owner":
        return None

    # Four headline numbers in one trip. Each bracketed SELECT is a scalar
    # subquery: it must return exactly one row and one column, and its value
    # drops into the column list like any other value. COUNT, SUM, a JOIN and
    # a date window in one statement — the most exam-worthy SQL in the app.
    stats = db.query_one(
        """
        select (select count(*) from orders
                 where placed_at::date = current_date)                   as orders_today,
               (select coalesce(sum(oi.qty * oi.price_at_order), 0)
                  from orders o
                  join order_items oi on oi.order_id = o.id
                 where o.placed_at::date = current_date)                 as money_today,
               (select count(*) from orders where status <> 'completed') as waiting,
               (select count(*) from payments
                 where target_kind = 'order' and status = 'claimed')     as to_check
        """
    )

    # The work: orders not yet completed, oldest first — the same fairness
    # rule the queue page uses, cut to the five that matter now.
    queue = db.query(
        """
        select o.id, o.status, u.name as customer, o.fulfillment,
               sum(oi.qty * oi.price_at_order) as total
          from orders o
          join users u on u.id = o.user_id
          join order_items oi on oi.order_id = o.id
         where o.status <> 'completed'
         group by o.id, u.name
         order by o.placed_at
         limit 5
        """
    )

    return {
        "eyebrow": "Owner",
        "title": "Haldiram dashboard",
        # The owner's guaranteed doors, rendered even on an empty database —
        # a dashboard with numbers but no way into the menu is a dead end.
        "actions": [
            {"label": "Order queue", "href": "/manage/orders"},
            {"label": "Menu editor", "href": "/manage/items"},
        ],
        "stats": [
            {"label": "Orders today", "value": stats["orders_today"], "foot": "since midnight"},
            {"label": "Money today", "value": "₹%s" % stats["money_today"], "foot": "UPI and counter"},
            {"label": "Waiting", "value": stats["waiting"], "foot": "not yet ready"},
            {"label": "Payments to check", "value": stats["to_check"], "foot": "UPI claims"},
        ],
        "panels": [
            {
                "title": "Needs your attention",
                "empty": "Nothing waiting — every order is completed.",
                "rows": [
                    {
                        "badge": o["status"],
                        "text": "#%s · %s" % (o["id"], o["customer"]),
                        "meta": "₹%s · %s" % (o["total"], o["fulfillment"]),
                        "href": "/manage/orders",
                        "action": "Open queue",
                    }
                    for o in queue
                ],
            },
        ],
    }


@app.route("/cart/add/<int:item_id>", methods=["POST"])
def cart_add(item_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    cart = session.get("cart", {})
    # Session dicts round-trip through JSON, so the key must be a string.
    key = str(item_id)
    cart[key] = int(cart.get(key, 0)) + 1
    session["cart"] = cart
    return redirect(url_for("home"))


@app.route("/cart/clear", methods=["POST"])
def cart_clear():
    session["cart"] = {}
    return redirect(url_for("home"))


@app.route("/checkout")
def checkout():
    """The step between the cart and the placed order.

    Fulfilment is decided HERE, before the order row exists — the address, the
    pickup time or the table number, whichever the chosen mode needs — and the
    payment method is ASKED here too, so one button places a fully-described
    order. Actually paying still happens after, on the order's own pay page,
    where the choice stays changeable until real money is in flight.
    """
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    lines, total = cart_lines()
    if not lines:
        return redirect(url_for("home"))
    return render_template("checkout.html", user=user, cart=lines, cart_total=total,
                           pay_enabled=payments.enabled(), error=None)


@app.route("/orders/place", methods=["POST"])
def place_order():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    lines, _total = cart_lines()
    if not lines:
        return redirect(url_for("home"))

    # The chosen mode decides which detail is required. All three fields
    # arrive from the one checkout form; '' becomes None BEFORE any binding,
    # and only the mode's own field is enforced — extra filled boxes are
    # ignored, never an error.
    fulfillment = request.form.get("fulfillment", "pickup")
    if fulfillment not in ("delivery", "pickup", "table"):
        fulfillment = "pickup"
    # The method chosen at checkout rides on the order row; the pay page can
    # still change it until a payment is claimed or verified.
    pay_method = request.form.get("pay_method", "counter")
    if pay_method not in ("upi", "counter") or not payments.enabled():
        pay_method = "counter"
    address = request.form.get("address", "").strip() or None
    pickup_time = request.form.get("pickup_time", "").strip() or None
    table_no = request.form.get("table_no", "").strip() or None

    error = None
    if fulfillment == "delivery" and not address:
        error = "Please enter a delivery address."
    elif fulfillment == "pickup" and not pickup_time:
        error = "Please enter a pickup time."
    elif fulfillment == "table" and not table_no:
        error = "Please enter a table number."
    if error:
        return render_template("checkout.html", user=user, cart=lines, cart_total=_total,
                               pay_enabled=payments.enabled(), error=error)

    order = db.insert_returning(
        """insert into orders (user_id, fulfillment, address, pickup_time, table_no, pay_method)
           values (%s, %s, %s, %s, %s, %s) returning id""",
        (user["id"], fulfillment, address, pickup_time,
         int(table_no) if table_no else None, pay_method),
    )
    for line in lines:
        # price_at_order copies today's price into the order line, so a menu
        # edit tomorrow can never rewrite a bill from yesterday.
        db.execute(
            """insert into order_items (order_id, item_id, qty, price_at_order)
               select %s, id, %s, price from items where id = %s""",
            (order["id"], line["qty"], line["id"]),
        )
    session["cart"] = {}
    # Straight to the money question. The order exists either way — payment
    # is a conversation about it, not a condition for it.
    return redirect(url_for("pay_choice", order_id=order["id"]))


@app.route("/orders/<int:order_id>/pay")
def pay_choice(order_id):
    """Order placed — now, how would you like to pay?

    UPI now, or cash — on delivery or at the counter, whichever way this
    order goes out. The page stays reachable from My orders, so the customer
    can change their mind right up until real money is in flight — a claimed
    or verified payment settles the question.
    """
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    # Their own order only, same rule as order_bill(). fulfillment rides
    # along so the cash wording can match how the order goes out.
    order = db.query_one(
        """
        select o.id, o.status, o.pay_method, o.fulfillment,
               sum(oi.qty * oi.price_at_order) as total,
               string_agg(i.name || ' x' || oi.qty, ', ' order by i.name) as summary
          from orders o
          join order_items oi on oi.order_id = o.id
          join items i on i.id = oi.item_id
         where o.id = %s and o.user_id = %s
         group by o.id
        """,
        (order_id, user["id"]),
    )
    if not order:
        return redirect(url_for("my_orders"))
    payment = payments.get("order", order_id)
    locked = bool(payment) and payment["status"] in ("claimed", "verified")
    # With UPI switched off there is no choice to make: everything is counter.
    method = order["pay_method"] if payments.enabled() else "counter"
    return render_template(
        "pay_choice.html", user=user, order=order, method=method, locked=locked,
        # Every pay_* variable the panel reads, in one call. The note is the
        # order NUMBER: nothing typed into a form belongs inside a upi:// link.
        **payments.context(order["total"], order["id"], "/pay/%s/claim" % order["id"],
                           payment, mode="customer", show=(method == "upi")),
    )


@app.route("/orders/<int:order_id>/pay/method", methods=["POST"])
def set_pay_method(order_id):
    """Saves the customer's answer to 'how would you like to pay?'."""
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    method = request.form.get("method", "")
    if method not in ("upi", "counter") or not payments.enabled():
        method = "counter"
    # NOT EXISTS is the lock: once a payment is claimed or verified, real
    # money is in flight and this UPDATE simply finds nothing to change.
    db.execute(
        """
        update orders
           set pay_method = %s
         where id = %s and user_id = %s
           and not exists (select 1 from payments p
                            where p.target_kind = 'order' and p.target_id = orders.id
                              and p.status in ('claimed', 'verified'))
        """,
        (method, order_id, user["id"]),
    )
    return redirect(url_for("pay_choice", order_id=order_id))


@app.route("/orders")
def my_orders():
    """Customer view: their own orders, newest first, with totals from SUM."""
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    orders = db.query(
        """
        select o.id, o.status, o.placed_at, o.pay_method,
               o.fulfillment, o.address, o.pickup_time, o.table_no,
               sum(oi.qty * oi.price_at_order) as total,
               string_agg(i.name || ' x' || oi.qty, ', ' order by i.name) as summary
          from orders o
          join order_items oi on oi.order_id = o.id
          join items i on i.id = oi.item_id
         where o.user_id = %s
         group by o.id
         order by o.placed_at desc
        """,
        (user["id"],),
    )
    # At most one payment row per order; a dict keyed by order id keeps the
    # page a single loop. Paying itself happens on each order's own pay page.
    paid = payments.by_kind("order")
    return render_template("my_orders.html", orders=orders, user=user, paid=paid)


# ── Money. The claim / verify / reject routes live in payments.py and are
# installed once; app.py only says WHICH row is being paid for and WHO may
# judge the payment. ─────────────────────────────────────────────────────

def order_bill(order_id, user):
    """What THIS customer owes for THIS order — or None if it is not theirs.

    Someone else's id in the URL must find nothing, which the user_id in the
    WHERE guarantees. The total comes from the order lines, never from
    anything a form could claim.
    """
    order = db.query_one(
        """
        select o.id, sum(oi.qty * oi.price_at_order) as total
          from orders o
          join order_items oi on oi.order_id = o.id
         where o.id = %s and o.user_id = %s
         group by o.id
        """,
        (order_id, user["id"]),
    )
    if not order:
        return None
    return {"amount": order["total"], "back": url_for("pay_choice", order_id=order_id)}


def is_owner(user, payment):
    """Only the owner may say whether money arrived."""
    return user["role"] == "owner"


# POST /pay/<order_id>/claim, /manage/payments/<id>/verify and /reject.
payments.install(app, "order", who=current_user, bill=order_bill, owner=is_owner,
                 manage="/manage/orders")


@app.route("/manage/orders/<int:order_id>/cash", methods=["POST"])
def cash_received(order_id):
    """Cash handed over at the counter.

    The owner is the witness, so payments.cash records it as verified straight
    away — there is no claim step to wait for — and pressing the button twice
    records exactly one payment. It also settles an abandoned UPI claim: cash
    in hand beats a reference nobody checked.
    """
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    order = db.query_one(
        """
        select o.id, sum(oi.qty * oi.price_at_order) as total
          from orders o
          join order_items oi on oi.order_id = o.id
         where o.id = %s
         group by o.id
        """,
        (order_id,),
    )
    if order:
        payments.cash("order", order_id, order["total"], user["id"])
    return redirect(url_for("manage_orders"))


@app.route("/manage/items", methods=["GET", "POST"])
def manage_items():
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    if request.method == "POST":
        db.execute(
            "insert into items (name, category, price) values (%s, %s, %s) on conflict (name) do nothing",
            (request.form["name"].strip(), request.form["category"].strip(),
             request.form["price"]),
        )
        return redirect(url_for("manage_items"))
    items = db.query("select id, name, category, price, is_available, image_url from items order by category, name")
    return render_template("manage_items.html", items=items, user=user, image_error=None)


@app.route("/manage/items/<int:item_id>/image", methods=["POST"])
def set_item_image(item_id):
    """Saves a pasted https image link for a menu item; empty clears it.

    The URL is data, not markup — the template escapes it like any other
    value, and only the https scheme is accepted, so a pasted http or
    javascript: link never reaches the page.
    """
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    url = request.form.get("image_url", "").strip()
    if url and (not url.startswith("https://") or len(url) > 300):
        items = db.query("select id, name, category, price, is_available, image_url from items order by category, name")
        return render_template(
            "manage_items.html", items=items, user=user,
            image_error="That link was not saved. Paste a direct https image link — right-click a picture on the web and choose 'Copy image address'.",
        )
    db.execute("update items set image_url = %s where id = %s", (url or None, item_id))
    return redirect(url_for("manage_items"))


@app.route("/manage/items/<int:item_id>/toggle", methods=["POST"])
def toggle_item(item_id):
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    db.execute("update items set is_available = not is_available where id = %s", (item_id,))
    return redirect(url_for("manage_items"))


@app.route("/manage/orders")
def manage_orders():
    """Owner view: the whole queue, oldest first — first come, first served."""
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    orders = db.query(
        """
        select o.id, o.status, o.placed_at, o.pay_method, u.name as customer,
               o.fulfillment, o.address, o.pickup_time, o.table_no,
               sum(oi.qty * oi.price_at_order) as total,
               string_agg(i.name || ' x' || oi.qty, ', ' order by i.name) as summary
          from orders o
          join users u on u.id = o.user_id
          join order_items oi on oi.order_id = o.id
          join items i on i.id = oi.item_id
         group by o.id, u.name
         order by o.placed_at
        """
    )
    paid = payments.by_kind("order")
    return render_template(
        "manage_orders.html", orders=orders, user=user, paid=paid,
        pay_enabled=payments.enabled(), mode="owner",
    )


@app.route("/manage/orders/<int:order_id>/advance", methods=["POST"])
def advance_order(order_id):
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect(url_for("home"))
    # One fixed path: placed -> preparing -> ready -> completed. A CASE keeps
    # the whole rule in one statement, and 'completed' simply stays put.
    db.execute(
        """update orders
              set status = case status
                             when 'placed' then 'preparing'
                             when 'preparing' then 'ready'
                             when 'ready' then 'completed'
                             else status
                           end
            where id = %s""",
        (order_id,),
    )
    return redirect(url_for("manage_orders"))


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
