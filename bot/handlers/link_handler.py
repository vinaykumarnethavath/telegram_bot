"""
Link Handler — processes YouTube URLs sent to the bot.
Now includes inline keyboard quick-action buttons after summary.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.transcript import TranscriptService, TranscriptError
from services.summarizer import SummarizerService
from storage.session_store import session_store

logger = logging.getLogger(__name__)

transcript_service = TranscriptService()
summarizer_service = SummarizerService()


def build_quick_actions_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard shown after every summary for quick access."""
    keyboard = [
        [
            InlineKeyboardButton("🔬 Deep Dive", callback_data="action_deepdive"),
            InlineKeyboardButton("✅ Action Points", callback_data="action_actionpoints"),
        ],
        [
            InlineKeyboardButton("🔑 Key Terms", callback_data="action_keyterms"),
            InlineKeyboardButton("🎭 Tone Analysis", callback_data="action_tone"),
        ],
        [
            InlineKeyboardButton("🌐 Change Language", callback_data="action_languages"),
            InlineKeyboardButton("🗑 Clear Session", callback_data="action_clear"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a message containing a YouTube URL."""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        video_id = transcript_service.extract_video_id(url)

        cached = session_store.get_cached_transcript(video_id)
        if cached:
            logger.info(f"Transcript cache hit for video_id={video_id}")
            title = cached["title"]
            transcript = cached["transcript"]
            chunks = cached["chunks"]
            await update.message.chat.send_action(ChatAction.TYPING)
        else:
            await update.message.reply_text(
                "🔍 _Fetching transcript from YouTube..._",
                parse_mode="Markdown",
            )
            await update.message.chat.send_action(ChatAction.TYPING)

            result = transcript_service.fetch_by_id(video_id)
            title = result.title
            transcript = result.transcript
            chunks = result.chunks

            session_store.cache_transcript(video_id, title, transcript, chunks=chunks)

        # Update session
        session.video_id = video_id
        session.video_title = title
        session.transcript = transcript
        session.qa_history = []
        session_store.save_session(session)

        # Summary generation
        await update.message.chat.send_action(ChatAction.TYPING)

        summary = summarizer_service.summarize(
            video_id=video_id,
            title=title,
            chunks=chunks,
            language=session.language,
        )

        session.summary = summary.text
        session_store.save_session(session)

        # Track usage stats
        session_store.increment_stat("videos_processed")

        # Send summary with inline keyboard
        await update.message.reply_text(
            summary.text,
            parse_mode="Markdown",
            reply_markup=build_quick_actions_keyboard(),
        )

        await update.message.reply_text(
            "💬 _Ask me anything about this video, or use the buttons above!_\n"
            "🌐 To switch language: `Summarize in Hindi`",
            parse_mode="Markdown",
        )

    except TranscriptError as e:
        logger.warning(f"Transcript error for {url}: {e}")
        await update.message.reply_text(str(e))

    except Exception as e:
        from services.groq_client import is_rate_limit_error
        if is_rate_limit_error(e):
            logger.warning(f"Rate limit exceeded for user {user_id}: {e}")
            await update.message.reply_text(
                "📈 *Groq Daily Limit Reached*\n\n"
                "You've hit the daily token limit for our high-quality model. "
                "The bot automatically tried a smaller model, but that limit is also reached.\n\n"
                "Please try again in a few hours! 🙏",
                parse_mode="Markdown"
            )
        else:
            logger.error(f"Unexpected error handling link {url}: {e}", exc_info=True)
            await update.message.reply_text(
                "⚠️ An unexpected error occurred. Please try again in a moment."
            )
