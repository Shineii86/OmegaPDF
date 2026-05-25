"""Telegram Bot API integration for sending PDFs directly to chats."""

from __future__ import annotations

import os
import requests
from typing import Optional

from config import REQUEST_TIMEOUT

TG_API_BASE = "https://api.telegram.org/bot{token}"
TG_MAX_FILE_MB = 50  # Telegram Bot API file size limit


def _api(token: str, method: str) -> str:
    return f"{TG_API_BASE.format(token=token)}/{method}"


def test_connection(bot_token: str, chat_id: str) -> bool:
    """Send a test message to verify bot token and chat ID are valid.

    Returns True on success, raises on failure.
    """
    resp = requests.post(
        _api(bot_token, "sendMessage"),
        data={"chat_id": chat_id, "text": "OmegaPDF connected! Ready to send manga PDFs."},
        timeout=REQUEST_TIMEOUT,
    )
    data = resp.json()
    if resp.status_code == 200 and data.get("ok"):
        return True
    raise RuntimeError(data.get("description", "Unknown Telegram error"))


def send_document(
    bot_token: str,
    chat_id: str,
    file_path: str,
    caption: Optional[str] = None,
) -> bool:
    """Send a file from disk to a Telegram chat.

    Args:
        bot_token: Telegram Bot API token.
        chat_id: Target chat/user ID.
        file_path: Path to the file to send.
        caption: Optional caption (max 1024 chars).

    Returns:
        True on success.

    Raises:
        FileNotFoundError: If file_path doesn't exist.
        RuntimeError: If Telegram API returns an error.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > TG_MAX_FILE_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Telegram limit is {TG_MAX_FILE_MB} MB.")

    payload = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption[:1024]

    fname = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        resp = requests.post(
            _api(bot_token, "sendDocument"),
            data=payload,
            files={"document": (fname, f, "application/pdf")},
            timeout=120,
        )

    data = resp.json()
    if resp.status_code == 200 and data.get("ok"):
        return True
    raise RuntimeError(data.get("description", "Unknown Telegram error"))


def send_bytes(
    bot_token: str,
    chat_id: str,
    file_bytes: bytes,
    filename: str,
    caption: Optional[str] = None,
) -> bool:
    """Send raw bytes as a file to a Telegram chat.

    Args:
        bot_token: Telegram Bot API token.
        chat_id: Target chat/user ID.
        file_bytes: Raw file content.
        filename: Filename for the uploaded document.
        caption: Optional caption (max 1024 chars).

    Returns:
        True on success.

    Raises:
        RuntimeError: If Telegram API returns an error.
    """
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > TG_MAX_FILE_MB:
        raise ValueError(f"File too large ({size_mb:.1f} MB). Telegram limit is {TG_MAX_FILE_MB} MB.")

    payload = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption[:1024]

    resp = requests.post(
        _api(bot_token, "sendDocument"),
        data=payload,
        files={"document": (filename, file_bytes, "application/pdf")},
        timeout=120,
    )

    data = resp.json()
    if resp.status_code == 200 and data.get("ok"):
        return True
    raise RuntimeError(data.get("description", "Unknown Telegram error"))
