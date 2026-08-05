import os
import re
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, render_template, abort, request, redirect, session, Response
from markupsafe import Markup, escape

from release_notes import RELEASE_NOTES

app = Flask(__name__)

# Railway terminates TLS at its edge and forwards plain HTTP internally (see
# enforce_https() below), so request.url_root/request.base_url report "http://" even
# though every real visitor is on https. Found 2026-08-04 -- every canonical tag, OG
# URL, and sitemap.xml entry from the new SEO routes was silently emitting http:// URLs,
# which actively hurts SEO (mixed-scheme canonicalization signals). Since this site only
# ever runs on one real domain, hardcoding it sidesteps needing to trust proxy headers
# (X-Forwarded-Proto) for URL generation entirely -- more predictable than relying on
# Railway's proxy setup never changing.
SITE_URL = "https://www.breachreportbot.com"


@app.context_processor
def inject_site_url():
    return {"site_url": SITE_URL}


@app.template_filter("markdown_lite")
def markdown_lite(text):
    """Render the small subset of Discord-flavored markdown RELEASE_NOTES bullets
    actually use (**bold**, `code`) as HTML. Escapes the raw text first so this stays
    safe even though the content is developer-authored, not user input."""
    text = str(escape(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)  # must run before single-* below
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return Markup(text)

# Required for signing the session cookie that holds the OAuth CSRF state (see /buy
# and /auth/discord/callback below). Must be set to a fixed value in Railway -- a
# per-process random fallback would break state verification the moment gunicorn
# runs more than one worker (each worker would sign with a different secret).
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


@app.before_request
def enforce_https():
    # Railway terminates TLS at its edge and forwards plain HTTP internally,
    # setting X-Forwarded-Proto to the scheme the visitor actually used.
    if request.headers.get("X-Forwarded-Proto", "https") == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=301)

# Set once the Discord Application/Client ID is known (Developer Portal -> General Information).
# Falls back to a placeholder link that just points at the docs page until it's configured.
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
INVITE_URL = (
    f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
    f"&permissions=347136&integration_type=0&scope=bot+applications.commands"
    if DISCORD_CLIENT_ID else "#"
)
# Same store-page link _store_page_view() builds in BreachReport.py, just built here
# independently since this is a separate codebase with no shared import.
DISCORD_STORE_URL = (
    f"https://discord.com/application-directory/{DISCORD_CLIENT_ID}/store"
    if DISCORD_CLIENT_ID else "#"
)

# Invite to the production "BreachReport" guild itself -- lets a visitor who isn't in
# any server with the bot come play with the existing community instead of needing
# their own server. Generic/no-expiry invite for now (2026-08-04); swap once the server
# has real onboarding channels (rules gate, start-here channel, etc.) built out.
SUPPORT_SERVER_INVITE_URL = "https://discord.gg/2Ms6rmt63Y"

# TEMPORARY (2026-07-30): the Lemon Squeezy store is still in test mode, pending identity
# verification -- a real checkout right now wouldn't charge anything, but would still
# trigger the real webhook and grant a real, fully-functional seat for free. Until
# verification clears and the live-mode API key is swapped in, the website's own OAuth+
# Lemon-Squeezy purchase flow (built below, left fully intact) is disabled and the buy
# button/route point at the Discord Store instead (a real, live SKU). Flip this back to
# True once Lemon Squeezy goes live -- no other code changes needed.
WEBSITE_PURCHASE_ENABLED = False

# ── Website purchase flow (user-scope only for now -- see BreachReport.py's
# SEAT_BUNDLES for the guild-scope bundles, not wired here yet) ────────────────
# "Sign in with Discord" (OAuth2, identify scope only) gets a real, verified Discord
# user ID server-side, then a Lemon Squeezy checkout is created directly with that ID
# embedded as custom_data -- identical in shape to what /subscribe already produces in
# the bot, so the existing webhook handler needs no changes to support this second
# purchase path.
DISCORD_CLIENT_SECRET   = os.environ.get("DISCORD_CLIENT_SECRET", "")
LEMON_SQUEEZY_API_KEY   = os.environ.get("LEMON_SQUEEZY_API_KEY", "")
LEMON_SQUEEZY_STORE_ID  = os.environ.get("LEMON_SQUEEZY_STORE_ID", "")
DISCORD_OAUTH_REDIRECT_URI = os.environ.get(
    "DISCORD_OAUTH_REDIRECT_URI", "https://www.breachreportbot.com/auth/discord/callback"
)

# Must match SEAT_BUNDLES["user"]["1"] in BreachReport.py -- keep in sync by hand if
# that ever changes, there's no shared source of truth between the two repos.
USER_1_VARIANT_ID  = 1954632
# The 7-day free trial is a Lemon Squeezy checkout feature -- Discord's Store has no
# equivalent, so drop the trial mention from the label while WEBSITE_PURCHASE_ENABLED
# is False and the button points at Discord instead. Comes back automatically once the
# flag flips back to True, no separate change needed then.
# Price changed $4.99 -> $3.99/month 2026-08-03 -- keep in sync by hand with the real
# Discord SKU price (Developer Portal) and BreachReport.py's own comments about it,
# there's no shared source of truth between the two repos.
USER_1_PRICE_LABEL = "$3.99/month" + (" (7-day free trial)" if WEBSITE_PURCHASE_ENABLED else "")


def _buy_flow_configured():
    """Whether the pricing card should show a real "Get Started" button vs. "Purchases
    open soon". While WEBSITE_PURCHASE_ENABLED is False, purchasing routes to the
    Discord Store instead of this site's own OAuth+Lemon-Squeezy checkout -- that only
    needs DISCORD_CLIENT_ID (the same requirement the "Add to Discord" button already
    has), not the full Lemon Squeezy config, which this bug was checking regardless of
    which flow was actually active. Found 2026-08-04: purchasing has been open via
    Discord since v5.63-b200, but the pricing card was still showing "open soon"."""
    if not WEBSITE_PURCHASE_ENABLED:
        return bool(DISCORD_CLIENT_ID)
    return all([DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, LEMON_SQUEEZY_API_KEY, LEMON_SQUEEZY_STORE_ID])


PAGES = {"terms", "privacy", "refunds", "about"}


@app.route("/")
def index():
    return render_template(
        "index.html", invite_url=INVITE_URL,
        buy_enabled=_buy_flow_configured(),
        buy_href=("/buy" if WEBSITE_PURCHASE_ENABLED else DISCORD_STORE_URL),
        user_1_price=USER_1_PRICE_LABEL,
        support_server_url=SUPPORT_SERVER_INVITE_URL,
    )


@app.route("/buy")
def buy():
    """Starts the Discord login step of the purchase flow. Only the user-scope 1-seat
    bundle is wired up right now -- guild-scope purchases need a server picker (the
    identify scope alone doesn't reveal guild memberships) and are deferred until
    there's real demand for buying that way instead of via /subscribe in Discord."""
    if not WEBSITE_PURCHASE_ENABLED:
        # Closes the exploit for anyone navigating straight to /buy, not just the
        # homepage button -- see WEBSITE_PURCHASE_ENABLED's own comment above.
        return redirect(DISCORD_STORE_URL)
    if not _buy_flow_configured():
        return render_template("buy_error.html", reason="Purchases aren't set up yet — check back soon."), 503
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))


@app.route("/auth/discord/callback")
def discord_callback():
    if request.args.get("error"):
        return render_template("buy_error.html", reason="Discord login was cancelled."), 400

    state = request.args.get("state")
    if not state or state != session.pop("oauth_state", None):
        return render_template(
            "buy_error.html", reason="Your login session expired or was invalid — please try again."
        ), 400

    code = request.args.get("code")
    if not code:
        return render_template("buy_error.html", reason="Missing authorization code from Discord."), 400

    token_resp = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_OAUTH_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if token_resp.status_code != 200:
        return render_template(
            "buy_error.html", reason="Couldn't verify your Discord login — please try again."
        ), 502
    access_token = token_resp.json().get("access_token")

    user_resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    discord_id = user_resp.json().get("id") if user_resp.status_code == 200 else None
    if not discord_id:
        return render_template(
            "buy_error.html", reason="Couldn't read your Discord account — please try again."
        ), 502

    checkout_resp = requests.post(
        "https://api.lemonsqueezy.com/v1/checkouts",
        json={
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "custom": {
                            "purchaser_discord_id": str(discord_id),
                            "scope": "user",
                            "bundle": "1",
                        }
                    }
                },
                "relationships": {
                    "store":   {"data": {"type": "stores",   "id": str(LEMON_SQUEEZY_STORE_ID)}},
                    "variant": {"data": {"type": "variants", "id": str(USER_1_VARIANT_ID)}},
                },
            }
        },
        headers={
            "Authorization": f"Bearer {LEMON_SQUEEZY_API_KEY}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        },
        timeout=10,
    )
    if checkout_resp.status_code >= 400:
        return render_template(
            "buy_error.html", reason="Couldn't create a checkout link — please try again in a moment."
        ), 502

    return redirect(checkout_resp.json()["data"]["attributes"]["url"])


@app.route("/guide")
def guide():
    return render_template("guide.html", invite_url=INVITE_URL)


@app.route("/changelog")
def changelog():
    return render_template("changelog.html", release_notes=RELEASE_NOTES)


# Every real, indexable page on the site -- kept as one list so robots.txt's Sitemap
# reference and sitemap.xml itself can't drift apart. (path, changefreq, priority).
# Deliberately excludes /buy and /auth/discord/callback -- functional redirect routes,
# not content, nothing there for a search engine to index.
SITE_PAGES = [
    ("/",          "weekly",  "1.0"),
    ("/guide",     "monthly", "0.8"),
    ("/about",     "monthly", "0.6"),
    ("/changelog", "weekly",  "0.5"),
    ("/terms",     "yearly",  "0.2"),
    ("/privacy",   "yearly",  "0.2"),
    ("/refunds",   "yearly",  "0.2"),
]


@app.route("/google893cee698c7d8f97.html")
def google_site_verification():
    return Response("google-site-verification: google893cee698c7d8f97.html", mimetype="text/html")


@app.route("/robots.txt")
def robots_txt():
    body = f"User-agent: *\nAllow: /\nDisallow: /buy\nDisallow: /auth/\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    urls = "\n".join(
        f"  <url>\n"
        f"    <loc>{SITE_URL}{path}</loc>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>"
        for path, changefreq, priority in SITE_PAGES
    )
    body = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    return Response(body, mimetype="application/xml")


@app.route("/<page>")
def legal_page(page):
    if page not in PAGES:
        abort(404)
    return render_template(f"{page}.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
