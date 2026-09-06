"""DoneJi's supervision layer. Python standard library only.

Your college can open a short, READ-ONLY look inside this app while it is
live — to check it works, and to check it is not being used for something it
should not be. You consented to that on DoneJi before shipping, you can see
every session that was ever opened, and every one of them carries a name and
a reason.

What a reviewer can do here: read pages. That is all. Every form, every
button, every POST is refused while a review session is active — see
_readonly_guard below, which is a before_request hook precisely so that a page
added tomorrow is covered without anyone remembering to protect it.

How the token works: DoneJi signs a short-lived message with the key it gave
you in DONEJI_REVIEW_KEY, and this file checks that signature. Nobody without
the key can forge one, and nothing here calls DoneJi at request time — your
app keeps running whether or not DoneJi is up.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

from flask import current_app, redirect, render_template, request, session, url_for
from jinja2 import TemplateNotFound

# How the footer describes a live review session.
REVIEW_SESSION_KEY = "doneji_review"


def _b64url_decode(text):
    """Decodes base64url, restoring the padding the format strips.

    Missing padding is the classic reason a token that verifies in one
    language fails in another, so it is restored explicitly here.
    """
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def verify_review_token(token):
    """The signed claims, or None. Never raises — a bad token is just a no.

    The signature covers the ENCODED payload, not the JSON, because two
    languages will never agree on key order or spacing but always agree on a
    byte sequence they both already hold.
    """
    key = os.environ.get("DONEJI_REVIEW_KEY", "")
    if not key or not token:
        return None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        return None
    signed = ("v1." + parts[1]).encode("ascii")
    expected = hmac.new(key.encode("utf-8"), signed, hashlib.sha256).digest()
    got = base64.urlsafe_b64encode(expected).rstrip(b"=").decode("ascii")
    # compare_digest, never ==: a plain comparison leaks, through how long it
    # takes to fail, roughly how much of the signature was right.
    if not hmac.compare_digest(got, parts[2]):
        return None
    try:
        claims = json.loads(_b64url_decode(parts[1]))
    except (ValueError, TypeError):
        return None
    if claims.get("v") != 1 or claims.get("scp") != "ro":
        return None
    if int(claims.get("exp", 0)) <= int(time.time()):
        return None
    return claims


def review_session():
    """The live review session, if there is one and it has not expired."""
    claims = session.get(REVIEW_SESSION_KEY)
    if not claims:
        return None
    if int(claims.get("exp", 0)) <= int(time.time()):
        session.pop(REVIEW_SESSION_KEY, None)
        return None
    return claims


PRIVACY_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>About this site</title>
<div style="max-width:38rem;margin:3rem auto;padding:0 1rem;font:16px/1.6 system-ui,sans-serif">
<h1 style="font-size:1.4rem">About this site</h1>
<p>This is a student project, built as coursework on DoneJi. It is run by the
student whose name appears on it, not by DoneJi and not by their college.</p>
<h2 style="font-size:1.05rem">Payments</h2>
<p>If this site asks you to pay, the money goes <strong>directly</strong> to the
owner's own UPI account. It is not a card payment, no company processes it,
there is no refund button, and neither DoneJi nor the college can reverse it.
Keep your UPI reference number.</p>
<h2 style="font-size:1.05rem">Who can see the records</h2>
<p>The owner can. A reviewer from the student's college may also open a short,
read-only session to check the work — the student agreed to this before
publishing, and can see a record of every such session. A reviewer cannot
change anything here.</p>
<h2 style="font-size:1.05rem">Getting in touch</h2>
<p>Contact the owner of this site directly. DoneJi does not hold this site's
data and cannot answer for it.</p>
</div>"""


def _app_module():
    """The student's own app.py, as a module object.

    Looked up through the Flask app's import_name, which is __name__ from
    app.py — 'app' when a server imports it, '__main__' when it is run
    directly. Both are in sys.modules by the time a request arrives.
    """
    return sys.modules.get(current_app.import_name)


def dashboard_data():
    """The numbers for /dashboard, from the app's own dashboard_stats().

    THE POINT OF THIS FUNCTION: the route belongs to the platform so that it
    cannot be deleted, and the numbers belong to the app so that they are
    actually about the app. A restaurant counts orders and rupees; a library
    counts free seats. None of that can live here, and none of it should.

    Looked up at REQUEST time, not when install() runs: install(app) is called
    near the top of app.py, and dashboard_stats() is usually defined further
    down, so at install time it does not exist yet.

    Returns None when the app says this visitor may not see the dashboard.
    """
    module = _app_module()
    stats = getattr(module, "dashboard_stats", None)
    if callable(stats):
        return stats()

    # No dashboard_stats() at all. Rather than a dead page, count the rows in
    # the app's own tables — true for any app, and honest about being generic.
    db = getattr(module, "db", None)
    if db is None:
        return {"title": "Dashboard", "stats": []}
    rows = db.query(
        """
        select table_name
          from information_schema.tables
         where table_schema = 'public' and table_type = 'BASE TABLE'
         order by table_name
        """
    )
    tiles = []
    for row in rows[:8]:
        name = row["table_name"]
        # The name comes from information_schema, not from a request, so it
        # cannot be attacker-chosen — but it still cannot be a parameter,
        # because an identifier never can be. Quoted, and nothing else.
        if not name.replace("_", "").isalnum():
            continue
        counted = db.query_one('select count(*) as n from "%s"' % name)
        tiles.append(
            {"label": name.replace("_", " ").title(), "value": counted["n"], "foot": "rows"}
        )
    return {
        "eyebrow": "Overview",
        "title": "Dashboard",
        "stats": tiles,
        "panels": [
            {
                "title": "Make this yours",
                "empty": "Add a dashboard_stats() function to app.py and this page will show your app's own numbers instead of row counts.",
                "rows": [],
            }
        ],
    }


def install(app):
    """Attaches the supervision layer. Called once, from app.py."""

    @app.route("/dashboard")
    def doneji_dashboard():
        """The owner's dashboard.

        Registered HERE, in a file the AI builder may never edit, because three
        real builds on 2026-08-17 each deleted this route from app.py while
        leaving the page in the bundle — the whole owner side of the app,
        unreachable, with every check reporting the build as perfect.

        What it shows is still entirely the app's: dashboard_stats() in app.py
        writes the labels, the SQL and the numbers.
        """
        dash = dashboard_data()
        if dash is None:
            # The app's own dashboard_stats() refused this visitor. Send them
            # to its login if it has one; otherwise home.
            target = "login" if "login" in current_app.view_functions else "home"
            if target not in current_app.view_functions:
                return redirect("/")
            return redirect(url_for(target))
        try:
            return render_template("dashboard.html", dash=dash)
        except TemplateNotFound:
            # The page was removed; the panel still renders on a bare shell.
            return render_template("_dashboard.html", dash=dash)

    def _dashboard_url(error, endpoint, values):
        """Makes url_for("dashboard") work even though the endpoint is ours.

        The route is registered as doneji_dashboard so that it can never
        collide with a dashboard() the app defines for itself. But everyone —
        the starters, and any code written later — writes url_for("dashboard"),
        and a login page that redirects there must not 500 over a name.

        url_build_error_handlers is Flask's own hook for exactly this: it runs
        only when a build has already failed, so an app that DOES define its
        own dashboard endpoint never reaches here.
        """
        if endpoint == "dashboard":
            return url_for("doneji_dashboard", **values)
        raise error

    app.url_build_error_handlers.append(_dashboard_url)

    @app.route("/.doneji/health")
    def doneji_health():
        """Alive, and still supervised. Carries no data about anybody."""
        return {"doneji": 1, "review": bool(os.environ.get("DONEJI_REVIEW_KEY"))}

    @app.route("/privacy")
    def doneji_privacy():
        return PRIVACY_HTML

    @app.route("/.doneji/review")
    def doneji_review():
        claims = verify_review_token(request.args.get("t", ""))
        if not claims:
            return "This supervision link is not valid, or it has expired.", 403
        # Clear FIRST. A reviewer who also happens to hold an owner login here
        # would otherwise keep it and walk straight through every role check.
        session.clear()
        session[REVIEW_SESSION_KEY] = {
            "rid": claims.get("rid"),
            "exp": int(claims.get("exp", 0)),
            "jti": claims.get("jti"),
        }
        return redirect(url_for("home"))

    @app.before_request
    def _readonly_guard():
        """Refuses every write while a review session is open.

        A before_request hook and not a decorator, on purpose: a decorator has
        to be remembered on each new route, and the one nobody remembers is
        the one that matters. This covers routes that do not exist yet.
        """
        claims = review_session()
        if not claims:
            return None
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        return "Read-only supervision session — this app is not changed from here.", 403

    @app.after_request
    def _disclosure(response):
        """Adds one honest line to the bottom of every page.

        Injected here rather than written into base.html because a page the
        generator invents tomorrow would not have it — and because while a
        reviewer is looking, the people using the site should be able to see
        that, which is the whole line between supervision and surveillance.
        """
        ctype = response.headers.get("Content-Type", "")
        # HTML only. Doing this to JSON or to the inline SVG of a payment QR
        # would corrupt it.
        if "text/html" not in ctype:
            return response
        claims = review_session()
        if claims:
            note = (
                "College supervision session &mdash; read only &mdash; "
                "expires " + time.strftime("%H:%M", time.localtime(claims["exp"]))
            )
        else:
            note = 'A student project on DoneJi. <a href="/privacy">About this site</a>.'
        body = response.get_data(as_text=True)
        line = (
            '<p style="text-align:center;font:12px system-ui,sans-serif;'
            'color:#94a3b8;padding:0 1rem 1.5rem;margin:0">' + note + "</p>"
        )
        if "</body>" in body:
            body = body.replace("</body>", line + "</body>", 1)
        else:
            body = body + line
        # set_data, not the header directly: Flask recomputes Content-Length
        # here, and a stale length truncates the page in the browser.
        response.set_data(body)
        return response
