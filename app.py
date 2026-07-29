import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, render_template, abort, request, redirect, session

app = Flask(__name__)

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
    "DISCORD_OAUTH_REDIRECT_URI", "https://breachreportbot.com/auth/discord/callback"
)

# Must match SEAT_BUNDLES["user"]["1"] in BreachReport.py -- keep in sync by hand if
# that ever changes, there's no shared source of truth between the two repos.
USER_1_VARIANT_ID  = 1954632
USER_1_PRICE_LABEL = "$4.99/month (7-day free trial)"


def _buy_flow_configured():
    return all([DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, LEMON_SQUEEZY_API_KEY, LEMON_SQUEEZY_STORE_ID])


PAGES = {"terms", "privacy", "refunds"}


@app.route("/")
def index():
    return render_template(
        "index.html", invite_url=INVITE_URL,
        buy_enabled=_buy_flow_configured(), user_1_price=USER_1_PRICE_LABEL,
    )


@app.route("/buy")
def buy():
    """Starts the Discord login step of the purchase flow. Only the user-scope 1-seat
    bundle is wired up right now -- guild-scope purchases need a server picker (the
    identify scope alone doesn't reveal guild memberships) and are deferred until
    there's real demand for buying that way instead of via /subscribe in Discord."""
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
