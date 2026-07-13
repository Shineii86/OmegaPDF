"""Telegram Bot — auto-responds to OmegaScans URLs with series info + download button.

Usage:
    TG_BOT_TOKEN=your_token python bot.py

When a user sends a URL like https://omegascans.org/series/{slug}/chapter-{num},
the bot replies with:
  - Cover photo
  - Title, Description, Status, Release year, Author, Total chapters
  - [Download PDF] button
"""

from __future__ import annotations

import os
import re
import logging
from io import BytesIO

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import OMEGA_BASE_URL, MEDIA_CDN, REQUEST_TIMEOUT
from fetcher import (
    get_series,
    get_chapters,
    get_chapter_images,
    download_images_concurrent,
)
from pdf_builder import images_to_pdf

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("OmegaBot")

# ── URL PATTERN ──────────────────────────────────────────────
URL_PATTERN = re.compile(
    r"omegascans\.org/series/(?P<slug>[^/]+)/chapter-(?P<chapter>\d+)",
    re.IGNORECASE,
)
SERIES_PATTERN = re.compile(
    r"omegascans\.org/series/(?P<slug>[^/\s]+)",
    re.IGNORECASE,
)


# ── HELPERS ──────────────────────────────────────────────────
def _omega_get(path: str) -> dict:
    url = f"{OMEGA_BASE_URL}{path}"
    r = requests.get(
        url,
        headers={"User-Agent": "OmegaPDF-Bot/3.1", "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _normalize_image_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{MEDIA_CDN}/{url.lstrip('/')}"


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]*>", "", raw)
    return re.sub(r"\s+", " ", text).strip()


def fetch_series_info(slug: str) -> dict | None:
    """Fetch normalized series metadata. Returns dict or None on error."""
    try:
        raw = _omega_get(f"/series/{slug}")
        schedule = raw.get("release_schedule") or {}
        days = [d.capitalize() for d, v in schedule.items() if v]
        meta = raw.get("meta") or {}
        tags = raw.get("tags") or []

        return {
            "title": raw.get("title", slug),
            "slug": raw.get("series_slug", slug),
            "description": _strip_html(raw.get("description", "")),
            "thumbnail": _normalize_image_url(raw.get("thumbnail", "")),
            "status": raw.get("status", "N/A"),
            "type": raw.get("series_type", ""),
            "rating": round(raw.get("rating", 0), 2),
            "totalViews": raw.get("total_views", 0),
            "author": raw.get("author", "") or "N/A",
            "studio": raw.get("studio", "") or "N/A",
            "releaseYear": raw.get("release_year", "") or "N/A",
            "releaseSchedule": days,
            "tags": [t["name"] if isinstance(t, dict) else t for t in tags],
            "chaptersCount": int(meta.get("chapters_count", "0") or "0"),
        }
    except Exception as e:
        logger.error(f"fetch_series_info({slug}): {e}")
        return None


def format_series_text(info: dict, chapter_name: str = "") -> str:
    """Format series info into a clean Telegram message."""
    desc = info["description"]
    if len(desc) > 300:
        desc = desc[:297] + "..."

    lines = [
        f"<b>{info['title']}</b>",
        "",
    ]
    if chapter_name:
        lines.append(f"📖 <b>Chapter:</b> {chapter_name}")
        lines.append("")

    if desc:
        lines.append(f"📝 <i>{desc}</i>")
        lines.append("")

    meta_lines = []
    if info.get("author") and info["author"] != "N/A":
        meta_lines.append(f"✍️ <b>Author:</b> {info['author']}")
    if info.get("status"):
        meta_lines.append(f"📊 <b>Status:</b> {info['status']}")
    if info.get("releaseYear") and info["releaseYear"] != "N/A":
        meta_lines.append(f"📅 <b>Year:</b> {info['releaseYear']}")
    if info.get("chaptersCount"):
        meta_lines.append(f"📚 <b>Chapters:</b> {info['chaptersCount']}")
    if info.get("type"):
        meta_lines.append(f"🏷️ <b>Type:</b> {info['type']}")
    if info.get("rating"):
        meta_lines.append(f"⭐ <b>Rating:</b> {info['rating']}")
    if info.get("releaseSchedule"):
        meta_lines.append(f"📆 <b>Schedule:</b> {', '.join(info['releaseSchedule'])}")

    lines.extend(meta_lines)
    return "\n".join(lines)


# ── HANDLERS ─────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>OmegaPDF Bot</b>\n\n"
        "Send me an OmegaScans URL and I'll show series info with a download button.\n\n"
        "URL format:\n"
        "<code>https://omegascans.org/series/&#123;slug&#125;/chapter-&#123;num&#125;</code>",
        parse_mode="HTML",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listen for OmegaScans URLs and respond with series info."""
    text = update.message.text or ""
    msg = update.message

    # Check for chapter URL
    m_ch = URL_PATTERN.search(text)
    if m_ch:
        slug = m_ch.group("slug")
        chapter_num = m_ch.group("chapter")
        chapter_slug = f"chapter-{chapter_num}"

        await msg.reply_chat_action("upload_photo")
        info = fetch_series_info(slug)
        if not info:
            await msg.reply_text("❌ Could not fetch series info. Check the URL.")
            return

        caption = format_series_text(info, f"Chapter {chapter_num}")
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📥 Download PDF", callback_data=f"dl:{slug}:{chapter_slug}")]]
        )

        thumb = info.get("thumbnail", "")
        if thumb:
            try:
                img_r = requests.get(thumb, timeout=REQUEST_TIMEOUT)
                if img_r.ok:
                    await msg.reply_photo(
                        photo=BytesIO(img_r.content),
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    return
            except Exception:
                pass

        # Fallback: text only
        await msg.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)
        return

    # Check for series-only URL
    m_ser = SERIES_PATTERN.search(text)
    if m_ser:
        slug = m_ser.group("slug")
        await msg.reply_chat_action("typing")
        info = fetch_series_info(slug)
        if not info:
            await msg.reply_text("❌ Could not fetch series info.")
            return

        caption = format_series_text(info)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📚 View Chapters", callback_data=f"chapters:{slug}")]]
        )

        thumb = info.get("thumbnail", "")
        if thumb:
            try:
                img_r = requests.get(thumb, timeout=REQUEST_TIMEOUT)
                if img_r.ok:
                    await msg.reply_photo(
                        photo=BytesIO(img_r.content),
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                    return
            except Exception:
                pass

        await msg.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data

    # Download PDF
    if data.startswith("dl:"):
        _, slug, chapter_slug = data.split(":", 2)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_chat_action("upload_document")
        await query.message.reply_text(f"⏳ Generating PDF for <b>{slug}</b> — {chapter_slug}...", parse_mode="HTML")

        try:
            ch = get_chapter_images(slug, chapter_slug)
            if not ch.get("success"):
                await query.message.reply_text("❌ Failed to fetch chapter images.")
                return

            images = ch["data"]["images"]
            series_title = ch["data"]["series"]["title"]
            ch_name = ch["data"]["name"]

            await query.message.reply_text(f"📥 Downloading {len(images)} pages...")
            img_bytes = download_images_concurrent(images)

            fname = f"{slug}_{chapter_slug}.pdf"
            images_to_pdf(
                img_bytes, fname,
                title=f"{series_title} — {ch_name}",
                author="OmegaPDF",
                subject=series_title,
                quality="medium",
            )

            import os
            size_mb = os.path.getsize(fname) / (1024 * 1024)
            with open(fname, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    caption=f"📄 {series_title} — {ch_name}\n{size_mb:.1f} MB • {len(images)} pages",
                )
            os.remove(fname)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            await query.message.reply_text(f"❌ Download failed: {e}")

    # List chapters
    elif data.startswith("chapters:"):
        slug = data.split(":", 1)[1]
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_chat_action("typing")

        try:
            info = fetch_series_info(slug)
            ch_list = get_chapters(slug)
            if not ch_list.get("success"):
                await query.message.reply_text("❌ Could not fetch chapters.")
                return

            chapters = ch_list["data"]
            title = info["title"] if info else slug
            text = f"<b>{title}</b> — {len(chapters)} chapters\n\n"
            for ch in chapters[:30]:
                free = "🆓" if ch.get("isFree") else "💰"
                text += f"{free} {ch['name']}\n"
            if len(chapters) > 30:
                text += f"\n... and {len(chapters) - 30} more"

            await query.message.reply_text(text, parse_mode="HTML")

        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}")


# ── MAIN ─────────────────────────────────────────────────────
def main():
    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        print("Error: Set TG_BOT_TOKEN environment variable.")
        print("  export TG_BOT_TOKEN=your_token_here")
        print("  python bot.py")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("OmegaPDF Bot started!")
    print("Send an OmegaScans URL to any chat where the bot is present.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
