"""UPI collection: the link, the QR, the reference check — and the three
money routes, installed once into any app.

Everything money-related that is the SAME in every app lives here: the
payments table's rows, the claim / verify / reject routes, and the context a
page needs to show the panel. What each app keeps for itself is WHICH row is
being paid for, and it says so in one small function: bill(target_id, user).

The one rule that matters: the UPI ID is read from the environment, never
written down here. An invented UPI ID is not a harmless placeholder — it may
be somebody's real account, and a customer's real money would arrive there.
"""
import os
from urllib.parse import quote

from flask import flash, redirect, request

import db


def enabled():
    """True only when the owner has set their own UPI ID.

    The whole panel is off until then, so an app that ships without this
    variable is a working app that takes cash, not a broken one.
    """
    return bool(os.environ.get("UPI_VPA", "").strip())


def payee():
    """The name shown inside the customer's UPI app before they confirm."""
    return os.environ.get("UPI_PAYEE_NAME", "").strip() or "This shop"


def pay_link(amount, note):
    """The upi:// deep link. On a phone, tapping it opens the UPI app.

    quote() escapes anything the note contains, so a shop name with a space
    or an ampersand cannot break the link apart into extra parameters.
    """
    vpa = os.environ.get("UPI_VPA", "").strip()
    return (
        "upi://pay?pa=" + quote(vpa)
        + "&pn=" + quote(payee())
        + "&am=" + quote("{:.2f}".format(float(amount)))
        + "&tn=" + quote(str(note))
        + "&cu=INR"
    )


def qr_svg(amount, note):
    """The same link as a QR, drawn as inline SVG, or None if it cannot be.

    A laptop cannot open a upi:// link — there is no UPI app on it — so on the
    device this course is taught on, the QR IS the payment method: the page is
    on the screen and the customer scans it with their own phone.

    Nothing the customer typed ever reaches this string; only the amount and
    an order number do. That is what makes it safe to render with |safe in the
    page, and it is the reason the note is a number and not a message.
    """
    try:
        import segno
    except ImportError:
        # No QR library on this host: fall back to the link alone rather than
        # taking the whole page down over a picture.
        return None
    qr = segno.make(pay_link(amount, note), micro=False)
    return qr.svg_inline(scale=4, border=2)


def clean_ref(raw):
    """The 12-digit UPI reference, or None if it is not one.

    UPI calls it an RRN; your bank app may label it UTR or 'UPI Ref No'. It is
    the same number, and it is always exactly 12 digits — which is all this
    can check. It proves the customer read something off a screen; it does not
    prove the money arrived. Only the owner's own bank app proves that, which
    is exactly why there is a separate verify step.
    """
    ref = "".join(str(raw).split())
    if len(ref) == 12 and ref.isdigit():
        return ref
    return None


# ── The payments table, one row per thing being paid for ──────────────────
#
# kind names the parent table in words ('order', 'booking', 'customer') and
# target_id is that row's id. There is no FOREIGN KEY because one table serves
# every app; the UNIQUE (target_kind, target_id) is what keeps it to one row.

def get(kind, target_id):
    """The one payment row for a thing, or None if nobody has paid yet."""
    return db.query_one(
        """select id, target_kind, target_id, amount, status, claimed_ref,
                  claimed_at, verified_at, note
             from payments where target_kind = %s and target_id = %s""",
        (kind, target_id),
    )


def by_kind(kind):
    """{target_id: payment row} for a whole list page, in one query."""
    paid = {}
    for row in db.query(
        """select id, target_id, amount, status, claimed_ref
             from payments where target_kind = %s""",
        (kind,),
    ):
        paid[row["target_id"]] = row
    return paid


def start(kind, target_id, amount):
    """Creates the row once. ON CONFLICT DO NOTHING plus the UNIQUE constraint
    is what makes this safe to run twice: opening a pay page twice cannot
    make two payments."""
    db.execute(
        """insert into payments (target_kind, target_id, amount)
           values (%s, %s, %s)
           on conflict (target_kind, target_id) do nothing""",
        (kind, target_id, amount),
    )


def claim(kind, target_id, amount, raw_ref, user_id=None, new_round=False):
    """The customer says they have paid, and types the 12-digit reference.

    Note what this does NOT do: check that the money arrived. Nothing here can
    — without a payment gateway there is no API to ask. All this records is a
    CLAIM, which is why the row goes to 'claimed' and not to 'verified'.
    Returns the cleaned reference, or None when what was typed is not one.

    new_round=True lets an already-verified row be claimed again — a khata
    collects many rounds against one running balance. Everything else keeps
    a verified payment exactly as it is.
    """
    ref = clean_ref(raw_ref)
    if not ref:
        return None
    start(kind, target_id, amount)
    # A verified payment is left alone unless the app asked for a new round.
    keep = "" if new_round else " and status <> 'verified'"
    db.execute(
        """update payments
              set amount = %s, status = 'claimed', claimed_ref = %s,
                  claimed_by = %s, claimed_at = now(),
                  verified_by = null, verified_at = null
            where target_kind = %s and target_id = %s""" + keep,
        (amount, ref, user_id, kind, target_id),
    )
    return ref


def verify(payment_id, user_id):
    """The owner looked in their own UPI app and the money was there.

    status = 'claimed' in the WHERE makes the button idempotent: a second
    press updates zero rows, and the function says so by returning False.
    """
    changed = db.execute(
        """update payments
              set status = 'verified', verified_by = %s, verified_at = now()
            where id = %s and status = 'claimed'""",
        (user_id, payment_id),
    )
    return changed > 0


def reject(payment_id):
    """The money was not there. The customer may send the reference again."""
    db.execute(
        "update payments set status = 'rejected' where id = %s and status = 'claimed'",
        (payment_id,),
    )


def cash(kind, target_id, amount, user_id, note="cash at counter"):
    """Cash handed over in person. The owner is the witness, so the row goes
    straight to 'verified' — no claim step to wait for. Idempotent: pressing
    the button twice cannot record the money twice, and it settles an
    abandoned UPI claim too — cash in hand beats a reference nobody checked."""
    start(kind, target_id, amount)
    db.execute(
        """update payments
              set status = 'verified', verified_by = %s, verified_at = now(), note = %s
            where target_kind = %s and target_id = %s and status <> 'verified'""",
        (user_id, note, kind, target_id),
    )


# ── What a page needs to show the panel ───────────────────────────────────

def context(amount, note, action, payment=None, mode="customer", error=None, show=True):
    """Every pay_* variable templates/_pay.html reads, for the CUSTOMER's side.

    Spread it into the render: render_template(page, **payments.context(...)).
    amount is what they owe, note is the order/booking NUMBER (never a name —
    nothing typed into a form belongs inside a upi:// link), action is the URL
    the "I have paid" form posts to. The QR and link appear only while there
    is something left to pay.
    """
    live = enabled() and show and not (payment and payment["status"] == "verified")
    return {
        "pay_enabled": enabled(),
        "pay_payee": payee(),
        "pay_amount": amount,
        "pay_link": pay_link(amount, note) if live else "",
        "pay_qr": qr_svg(amount, note) if live else None,
        "pay_action": action,
        "pay_error": error,
        "payment": payment,
        "mode": mode,
    }


def owner_context(payment, verify_action, reject_action):
    """The OWNER's side of the panel: what was claimed, and the two buttons."""
    return {
        "pay_enabled": enabled(),
        "mode": "owner",
        "payment": payment,
        "pay_verify_action": verify_action,
        "pay_reject_action": reject_action,
    }


# ── The three money routes, installed once ────────────────────────────────

def install(app, kind, who, bill, owner, manage, on_verified=None):
    """Attaches the claim / verify / reject routes to the app.

    The app hands in what only it knows:
      who()                 -> the logged-in user row, or None
      bill(target_id, user) -> {"amount": ..., "back": "/url"} when THIS user
                               may pay for THIS thing, else None (not theirs,
                               free, or unknown — every one of those is a
                               silent redirect, never a crash)
      owner(user, payment)  -> True when this user may judge this payment
      manage                -> the URL to return to after verify/reject, or a
                               function of the payment row that builds one
      on_verified(payment)  -> optional: what else to record when money is
                               confirmed (a khata writes the jama line)

    The URLs are fixed so every page can rely on them:
      POST /pay/<target_id>/claim
      POST /manage/payments/<payment_id>/verify
      POST /manage/payments/<payment_id>/reject
    """

    def _row(payment_id):
        return db.query_one(
            """select id, target_kind, target_id, amount, status, claimed_ref, note
                 from payments where id = %s and target_kind = %s""",
            (payment_id, kind),
        )

    def _back(payment):
        return manage(payment) if callable(manage) else manage

    @app.route("/pay/<int:target_id>/claim", methods=["POST"])
    def claim_payment(target_id):
        user = who()
        if not user or not enabled():
            return redirect("/")
        due = bill(target_id, user) if bill else None
        if not due:
            return redirect("/")
        ref = claim(kind, target_id, due["amount"], request.form.get("ref", ""), user["id"],
                    new_round=bool(due.get("new_round")))
        if not ref:
            flash("That did not look like a 12-digit UPI reference — check it in your UPI app and try again.", "warning")
        return redirect(due["back"])

    @app.route("/manage/payments/<int:payment_id>/verify", methods=["POST"])
    def verify_payment(payment_id):
        user = who()
        payment = _row(payment_id)
        if not user or not payment or not owner(user, payment):
            return redirect("/")
        if verify(payment_id, user["id"]) and on_verified:
            on_verified(payment)
        return redirect(_back(payment))

    @app.route("/manage/payments/<int:payment_id>/reject", methods=["POST"])
    def reject_payment(payment_id):
        user = who()
        payment = _row(payment_id)
        if not user or not payment or not owner(user, payment):
            return redirect("/")
        reject(payment_id)
        return redirect(_back(payment))
