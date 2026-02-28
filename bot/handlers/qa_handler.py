"""
Q&A Handler — handles follow-up questions about the current video.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.qa import QAService
from services.language import LanguageService
from storage.session_store import session_store

logger = logging.getLogger(__name__)

qa_service = QAService()
language_service = LanguageService()


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a follow-up question about the current video."""
    user_id = update.effective_user.id
    question = update.message.text.strip()
    session = session_store.get_session(user_id)

    # Check if a language switch is being requested
    lang_request = language_service.detect_language_request(question)
    if lang_request:
        session.language = lang_request
        session_store.save_session(session)
        lang_name = language_service.get_display_name(lang_request)
        
        await update.message.reply_text(
            f"🌐 Language switched to *{lang_name}*!",
            parse_mode="Markdown",
        )

        # If a video is already active, regenerate the summary in the new language
        if session.video_id:
            await update.message.chat.send_action(ChatAction.TYPING)
            from services.summarizer import SummarizerService
            from bot.handlers.link_handler import build_quick_actions_keyboard
            summarizer = SummarizerService()
            cached = session_store.get_cached_transcript(session.video_id)
            if cached:
                summary = summarizer.summarize(
                    video_id=session.video_id,
                    title=session.video_title,
                    chunks=cached["chunks"],
                    language=session.language
                )
                session.summary = summary.text
                session_store.save_session(session)
                await update.message.reply_text(
                    summary.text,
                    parse_mode="Markdown",
                    reply_markup=build_quick_actions_keyboard(session.language)
                )
        return

    # Check if user has loaded a video
    if not session.transcript:
        await update.message.reply_text(
            "📎 Please send me a YouTube link first!\n"
            "Example: `https://youtube.com/watch?v=dQw4w9WgXcQ`",
            parse_mode="Markdown",
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        answer = qa_service.answer(
            question=question,
            transcript=session.transcript,
            title=session.video_title or "YouTube Video",
            qa_history=session.qa_history,
            language=session.language,
        )

        # Store Q&A in session history + update stats
        session_store.add_qa(user_id, question, answer)
        session_store.increment_stat("questions_answered")

        await update.message.reply_text(answer, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Q&A error for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "⚠️ Sorry, I couldn't answer that. Please try rephrasing your question."
        )
