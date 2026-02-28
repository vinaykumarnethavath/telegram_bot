"""
Callback Handler — handles InlineKeyboard button presses after summary.

Buttons available:
  🔬 Deep Dive        → runs /deepdive flow
  ✅ Action Points    → runs /actionpoints flow
  🔑 Key Terms        → runs /keyterms flow
  🎭 Tone Analysis    → runs /tone flow
  🌐 Change Language  → shows language options
  🗑 Clear Session    → clears user session
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from storage.session_store import session_store

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route inline keyboard button presses."""
    query = update.callback_query
    await query.answer()  # Always acknowledge the callback

    data = query.data
    user_id = update.effective_user.id

    if data == "action_deepdive":
        from bot.handlers.command_handlers import deepdive_command
        # Create a fake update that uses the callback message
        await query.message.reply_text("🔬 _Running deep dive..._", parse_mode="Markdown")
        await _run_deepdive(query.message, user_id)

    elif data == "action_actionpoints":
        await query.message.reply_text("📋 _Extracting action points..._", parse_mode="Markdown")
        await _run_actionpoints(query.message, user_id)

    elif data == "action_keyterms":
        await query.message.reply_text("🔑 _Extracting key terms..._", parse_mode="Markdown")
        await _run_keyterms(query.message, user_id)

    elif data == "action_tone":
        await query.message.reply_text("🎭 _Analysing tone..._", parse_mode="Markdown")
        await _run_tone(query.message, user_id)

    elif data == "action_languages":
        from services.language import LanguageService
        svc = LanguageService.__new__(LanguageService)  # avoid client init
        from services.language import LANGUAGE_DISPLAY_NAMES
        lines = ["🌐 *Switch Language — type one of these commands:*\n"]
        for code, name in LANGUAGE_DISPLAY_NAMES.items():
            flag = "🇬🇧" if code == "en" else "🇮🇳"
            lines.append(f"{flag} `/language {code}` — {name}")
        await query.message.reply_text("\n".join(lines), parse_mode="Markdown")

    elif data == "action_clear":
        session_store.clear_session(user_id)
        await query.message.reply_text(
            "🗑 _Session cleared! Send a new YouTube link to start fresh._",
            parse_mode="Markdown",
        )


async def _run_deepdive(message, user_id: int):
    from services.analysis import AnalysisService
    session = session_store.get_session(user_id)
    if not session.transcript:
        await message.reply_text("📭 No video loaded. Send a YouTube link first!")
        return

    await message.chat.send_action(ChatAction.TYPING)
    svc = AnalysisService()
    result = svc.deep_dive(session.video_title or "Video", session.transcript, session.language)
    await message.reply_text(result, parse_mode="Markdown")


async def _run_actionpoints(message, user_id: int):
    from services.analysis import AnalysisService
    session = session_store.get_session(user_id)
    if not session.transcript:
        await message.reply_text("📭 No video loaded. Send a YouTube link first!")
        return

    await message.chat.send_action(ChatAction.TYPING)
    svc = AnalysisService()
    result = svc.action_points(session.video_title or "Video", session.transcript, session.language)
    await message.reply_text(result, parse_mode="Markdown")


async def _run_keyterms(message, user_id: int):
    from services.keyterms import KeyTermsService

    session = session_store.get_session(user_id)
    if not session.transcript:
        await message.reply_text("📭 No video loaded. Send a YouTube link first!")
        return

    await message.chat.send_action(ChatAction.TYPING)
    svc = KeyTermsService()
    result = svc.extract(session.video_title or "Video", session.transcript, session.language)
    await message.reply_text(result, parse_mode="Markdown")


async def _run_tone(message, user_id: int):
    from services.sentiment import SentimentService

    session = session_store.get_session(user_id)
    if not session.transcript:
        await message.reply_text("📭 No video loaded. Send a YouTube link first!")
        return

    await message.chat.send_action(ChatAction.TYPING)
    svc = SentimentService()
    result = svc.analyse(session.video_title or "Video", session.transcript, session.language)
    await message.reply_text(result, parse_mode="Markdown")
