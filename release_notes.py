# Manually kept in sync with BreachReport.py's own RELEASE_NOTES dict -- there is no
# shared codebase/DB between the bot and this site, so this is a deliberate, reviewed
# subset, not an automatic mirror. Whenever a new version ships with real customer-facing
# notes, copy the relevant bullets in here too (reworded if the original text leaks any
# internal architecture/mechanics -- see the reasoning below for what's been left out).
#
# Deliberately excluded from this list (kept in the bot's own RELEASE_NOTES for the
# in-Discord announcement history, but not shown here): pure internal bug-chase entries
# that expose implementation details (constant names, DB table names, migration
# numbers) with no distinct end-user-visible takeaway beyond what's already covered by a
# neighboring entry, and anything describing the old single-tenant desktop-app era
# (local setup wizard, Windows Credential Manager) that no longer reflects the product.
#
# Ordered newest-first, same as the in-Discord announcement.
RELEASE_NOTES = [
    ("6.0", [
        "🎮 **Quick Match and Unranked leaderboards now update live** — records, personal bests, and the nightly leaderboard now refresh the moment a match is detected, the same way Ranked already did. No more waiting until end of day to see it reflected.",
        "🛡️ **More reliable match detection** — a rare timing issue that could occasionally cause a match to go untracked has been fixed. Day-to-day tracking should feel more consistent across all modes.",
        "📅 **\"Tonight\" is now \"Today\"** — small wording update across leaderboards and stat commands to better reflect always-on tracking.",
    ]),
    ("5.64", [
        "🎮 **Console support** — BreachReport now tracks Xbox and PlayStation players too. Pick your platform when linking with `/addplayer`.",
    ]),
    ("5.63", [
        "🎮 **Quick Match and Unranked tracking are here** — BreachReport now tracks all of R6's core modes, not just Ranked. New `/setmodes` command (admin-only) lets each server independently turn on Quick Match and/or Unranked tracking, and a **Combined** view that sums whichever modes you've enabled. Ranked stays on by default for every server — nothing changes unless you opt in.",
        "🏆 **Every leaderboard now supports mode selection** — `/leaderboard`, `/monthlyleader`, `/seasonleader`, and `/lifetimeleaderboard` all take an optional mode choice (Ranked / Quick Match / Unranked / Combined). Leave it blank and you'll see every mode your server has enabled; pick one to see just that mode.",
        "📊 **Personal stats and records go mode-wide too** — `/records`, `/alltime`, `/lifetimestats`, `/monthlypersonalrecords`, `/monthlyalltimerecords`, `/seasonpersonalrecords`, and `/seasonalltimerecords` all follow the same pattern, including daily best-day-ever records.",
        "🏅 **Manual stats (MVP / Target Ban / Funny TK) are mode-scoped** — `/addmvp` and friends now apply to whichever mode you specify. If your server only tracks Ranked, nothing changes; if you've turned on multiple modes, you'll be asked which one.",
        "⚡ **Ranked stats update noticeably faster** — kills, deaths, wins, and losses now come from a faster Ubisoft data source instead of the one that could lag up to an hour behind. Detail stats (assists, headshots, clutches, etc.) still follow Ubisoft's own timing.",
        "🐛 **Fixed: an account re-link could occasionally show wildly wrong negative stats for a moment** — a rare edge case around stale cached data has been closed off; day-to-day tracking is unaffected.",
    ]),
    ("5.56", [
        "🎖️ **Headshot count restored on all leaderboards** — HS count (🎖️ X HS) now appears alongside HS% on nightly, monthly, season, and lifetime leaderboards. Each headshot still earns +1 pt.",
        "🎯 **HS% winner now marked with ★** — the player with the best HS% each session has a ★ next to their percentage so it's immediately clear who earned the Best HS% bonus.",
        "🚫 **Target Bans now shown as 🚫 TB** — previously used 🎯 (same as HS%), causing confusion. Target Bans now use 🚫 across all leaderboards and session summaries.",
    ]),
    ("5.54", [
        "☠️ **First Deaths now tracked on all leaderboards** — how often you die first in a round. Displayed on nightly, monthly, season, and lifetime leaderboards as ☠️ FD. Tracked as a personal and all-time record. Configurable via `/setpoints` → *First Death* (default 0 pts — tracked but not penalized; set negative to penalize).",
    ]),
    ("5.53", [
        "🎯 **HS% (Headshot %) now tracked on all leaderboards** — computed from headshots ÷ kills. Displayed on nightly, monthly, season, and lifetime leaderboards. The player with the best HS% each session earns a configurable bonus (default **+3 pts**) — similar to the K/D bonus. Adjustable via `/setpoints` → *Best HS% Bonus*. HS% is also tracked as a personal and all-time daily, monthly, and season record.",
    ]),
    ("5.52", [
        "📊 **`/lifetimeleaderboard`** — new slash command that posts the all-time lifetime leaderboard to the stats channel on demand (same view as end-of-session). For stat-sorted views, `/lifetimeleader` still offers a dropdown to rank by Kills, K/D, First Bloods, ACEs, etc.",
    ]),
    ("5.51", [
        "📊 **All-Time Lifetime Leaderboard now posted at session end** — after the season standings, the bot now posts a full lifetime leaderboard showing cumulative totals across every session ever played (points, K/D, W/L, sessions, and extras). Only fires if there is session activity — skipped on empty sessions.",
    ]),
    ("5.50", [
        "🐛 **Fixed an issue that could inflate season records with data carried over from a prior season.**",
    ]),
    ("5.49", [
        "🐛 **Fixed a bug where the season leaderboard could briefly show stats from the previous season.**",
    ]),
    ("5.48", [
        "🐛 **Fixed negative win/loss counts briefly appearing right after a new ranked season starts.**",
    ]),
    ("5.47", [
        "🐛 **Fixed record embed title said BROKEN when the record was only tied** — the daily, monthly, and season all-time record embeds now show the correct title: **TIED** when the new value matches the existing record, **SET** for a brand-new first-ever record, and **BROKEN** only when the old record is actually surpassed.",
    ]),
    ("5.31", [
        "🤝 **All-time record ties now credited to all players** — when multiple players match the same all-time, monthly, or season record in the same session, every player who tied is now announced (e.g., win streak of 4 shared by two squadmates). Previously only the first player to set the record was credited.",
    ]),
]
