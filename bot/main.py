"""
Bot main entry point — wires all handlers including new CallbackQueryHandler.
"""

import os
import logging
import re

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.handlers.link_handler import handle_youtube_link
from bot.handlers.qa_handler import handle_question
from bot.handlers.callback_handler import handle_callback_query
from bot.handlers.command_handlers import (
    start_command,
    help_command,
    summary_command,
    deepdive_command,
    actionpoints_command,
    keyterms_command,
    tone_command,
    language_command,
    languages_command,
    clear_command,
    reset_command,
    stats_command,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

YOUTUBE_URL_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/\S+",
    re.IGNORECASE,
)

BOT_COMMANDS = [
    BotCommand("start",        "Welcome & quick start"),
    BotCommand("help",         "Usage guide"),
    BotCommand("summary",      "Re-send last summary"),
    BotCommand("deepdive",     "In-depth video analysis"),
    BotCommand("actionpoints", "Extract actionable steps"),
    BotCommand("keyterms",     "Key terms & glossary"),
    BotCommand("tone",         "Tone & sentiment analysis"),
    BotCommand("language",     "Switch response language"),
    BotCommand("languages",    "List all supported languages"),
    BotCommand("clear",        "Clear session & start fresh"),
    BotCommand("reset",        "Force reset & clear history"),
    BotCommand("stats",        "Bot usage statistics"),
]


async def post_init(application: Application):
    """Set bot command menu shown in Telegram."""
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("✅ Bot commands registered in Telegram menu")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN not set in .env!")

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("❌ GROQ_API_KEY not set in .env!")

    logger.info("🚀 Starting YouTube Summarizer Bot (Groq powered)...")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # --- Command Handlers ---
    app.add_handler(CommandHandler("start",        start_command))
    app.add_handler(CommandHandler("help",         help_command))
    app.add_handler(CommandHandler("summary",      summary_command))
    app.add_handler(CommandHandler("deepdive",     deepdive_command))
    app.add_handler(CommandHandler("actionpoints", actionpoints_command))
    app.add_handler(CommandHandler("keyterms",     keyterms_command))
    app.add_handler(CommandHandler("tone",         tone_command))
    app.add_handler(CommandHandler("language",     language_command))
    app.add_handler(CommandHandler("languages",    languages_command))
    app.add_handler(CommandHandler("clear",        clear_command))
    app.add_handler(CommandHandler("reset",        reset_command))
    app.add_handler(CommandHandler("stats",        stats_command))

    # --- Inline Keyboard Callbacks ---
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # --- Message Handlers ---
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(YOUTUBE_URL_REGEX),
            handle_youtube_link,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(YOUTUBE_URL_REGEX),
            handle_question,
        )
    )

    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
