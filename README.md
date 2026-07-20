# BreachReportBot Site

Landing page for BreachReportBot (breachreportbot.com) — Flask app, deployed to Railway
via git push (same pattern as the main bot).

## Local dev

```
pip install -r requirements.txt
python app.py
```

Serves at http://localhost:8000

## Environment variables

- `DISCORD_CLIENT_ID` — the bot's Application/Client ID (Discord Developer Portal ->
  General Information). Without it, the invite button links to `#` as a placeholder.
- `PORT` — set automatically by Railway; defaults to 8000 locally.

## Status

Phase 1 scaffold: static-content landing page + Terms/Privacy/Refund placeholder pages
(marked as drafts, not legally reviewed). Pricing shown as "TBD" until real Lemon
Squeezy pricing is decided. No backend/database — deliberately kept dumb per the
security discussion (minimal attack surface, no dynamic input processing).
