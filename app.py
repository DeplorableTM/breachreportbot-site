import os
from flask import Flask, render_template, abort

app = Flask(__name__)

# Set once the Discord Application/Client ID is known (Developer Portal -> General Information).
# Falls back to a placeholder link that just points at the docs page until it's configured.
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
INVITE_URL = (
    f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
    f"&permissions=277025441856&scope=bot%20applications.commands"
    if DISCORD_CLIENT_ID else "#"
)

PAGES = {"terms", "privacy", "refunds"}


@app.route("/")
def index():
    return render_template("index.html", invite_url=INVITE_URL)


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
