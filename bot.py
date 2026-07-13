"""Simple Telegram Bot — sends comics info card when someone posts a URL.

Usage:
    TG_BOT_TOKEN=your_token python bot.py
"""

import os
import re
import logging
from io import BytesIO

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from config import OMEGA_BASE_URL, MEDIA_CDN, REQUEST_TIMEOUT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Bot")

URL_RE = re.compile(r"omegascans\.org/series/(?P<slug>[^/\s]+)", re.IGNORECASE)


def api(path):
    r = requests.get(f"{OMEGA_BASE_URL}{path}", headers={"User-Agent": "Bot/1.0"}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def norm_url(u):
    if not u: return ""
    if u.startswith("http"): return u
    return f"{MEDIA_CDN}/{u.lstrip('/')}"


def strip_html(s):
    if not s: return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", s)).strip()


def get_info(slug):
    raw = api(f"/series/{slug}")
    meta = raw.get("meta") or {}
    return {
        "title": raw.get("title", slug),
        "slug": raw.get("series_slug", slug),
        "description": strip_html(raw.get("description", "")),
        "thumbnail": norm_url(raw.get("thumbnail", "")),
        "status": raw.get("status", ""),
        "author": raw.get("author", "") or "N/A",
        "year": raw.get("release_year", "") or "N/A",
        "type": raw.get("series_type", ""),
        "chapters": int(meta.get("chapters_count", "0") or "0"),
    }


def card_text(i):
    d = i["description"][:300] + "..." if len(i["description"]) > 300 else i["description"]
    lines = [f"<b>{i['title']}</b>"]
    if d:
        lines += ["", f"<i>{d}</i>"]
    lines += ["", f"<b>Status:</b> {i['status']}", f"<b>Year:</b> {i['year']}",
              f"<b>Author:</b> {i['author']}", f"<b>Chapters:</b> {i['chapters']}"]
    return "\n".join(lines)


async def msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    text = m.text or ""
    match = URL_RE.search(text)
    if not match:
        return

    slug = match.group("slug")
    try:
        info = get_info(slug)
    except Exception as e:
        await m.reply_text("❌ Error fetching info.")
        return

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📥 Download PDF", callback_data=f"dl:{slug}")]]
    )

    thumb = info["thumbnail"]
    if thumb:
        try:
            img = requests.get(thumb, timeout=15)
            if img.ok:
                await m.reply_photo(
                    photo=BytesIO(img.content),
                    caption=card_text(info),
                    parse_mode="HTML",
                    reply_markup=kb,
                )
                return
        except Exception:
            pass

    await m.reply_text(card_text(info), parse_mode="HTML", reply_markup=kb)


async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    slug = q.data.split(":", 1)[1]
    await q.edit_message_reply_markup(reply_markup=None)
    await q.message.reply_text(f"📥 Sending chapters list for <b>{slug}</b>...", parse_mode="HTML")

    from fetcher import get_chapters
    try:
        ch = get_chapters(slug)
        if not ch.get("success"):
            return
        text = f"<b>{slug}</b> — {len(ch['data'])} chapters\n\n"
        for c in ch["data"][:30]:
            f = "🆓" if c.get("isFree") else "💰"
            text += f"{f} {c['name']}\n"
        await q.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await q.message.reply_text(f"❌ {e}")


def main():
    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        print("Set TG_BOT_TOKEN env var first.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    print("Bot running!")
    app.run_polling()


if __name__ == "__main__":
    main()
