import os
from flask import Flask, render_template, abort, request, redirect

app = Flask(__name__)


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

PAGES = {"terms", "privacy", "refunds"}


@app.route("/")
def index():
    return render_template("index.html", invite_url=INVITE_URL)


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
