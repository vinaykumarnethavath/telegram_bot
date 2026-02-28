"""
Command Handlers — all bot commands using Groq LLaMA.

Commands:
  /start, /help, /summary, /deepdive, /actionpoints, /language, /languages,
  /keyterms, /tone, /clear, /stats
"""

import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from services.language import LanguageService, SUPPORTED_LANGUAGES, LANGUAGE_DISPLAY_NAMES
from storage.session_store import session_store

logger = logging.getLogger(__name__)
language_service = LanguageService()

GROQ_QUALITY_MODEL = os.getenv("GROQ_QUALITY_MODEL", "llama-3.3-70b-versatile")

MESSAGES = {
    "en": {
        "welcome": "👋 *Welcome, {name}!*\n\nYour personal AI research assistant for YouTube:\n\n🎥 Send any YouTube link → structured summary\n💬 Ask follow-up questions → grounded answers\n🌐 Multi-language — EN, HI, KN, TA, TE, MR\n🔬 Deep dive, 🔑 Key terms, 🎭 Tone analysis\n\n*Commands:*\n/summary · /deepdive · /actionpoints\n/keyterms · /tone · /clear · /stats\n/language · /languages · /help\n\nSend a YouTube link to get started 🚀",
        "help": "📖 *YouTube AI Bot — Command Guide*\n\n*📥 Input:*\nSend any YouTube URL to get a summary\n\n*❓ Q&A:*\nAsk anything after loading a video\n\n*⚡ Commands:*\n/summary — Re-send last summary\n/deepdive — In-depth analysis\n/actionpoints — Actionable items\n/keyterms — Key terms & glossary\n/tone — Tone & sentiment analysis\n/clear — Reset your session\n/reset — Force reset bot state\n/stats — Usage statistics\n/language <name> — Switch language\n/languages — All supported languages\n\n*🌐 Languages:* EN · HI · KN · TA · TE · MR\nSwitch: `Summarize in Hindi` or `/language kannada`"
    },
    "hi": {
        "welcome": "👋 *नमस्ते, {name}!*\n\nआपका व्यक्तिगत YouTube AI अनुसंधान सहायक:\n\n🎥 कोई भी YouTube लिंक भेजें → संरचित सारांश\n💬 अनुवर्ती प्रश्न पूछें → प्रमाणित उत्तर\n🌐 बहु-भाषा — EN, HI, KN, TA, TE, MR\n🔬 गहरा विश्लेषण, 🔑 मुख्य शब्द, 🎭 स्वर विश्लेषण\n\n*कमांड:*\n/summary · /deepdive · /actionpoints\n/keyterms · /tone · /clear · /stats\n/language · /languages · /help\n\nशुरू करने के लिए एक YouTube लिंक भेजें 🚀",
        "help": "📖 *YouTube AI बॉट — कमांड गाइड*\n\n*📥 इनपुट:*\nसारांश प्राप्त करने के लिए कोई भी YouTube URL भेजें\n\n*❓ प्रश्नोत्तर:*\nवीडियो लोड करने के बाद कुछ भी पूछें\n\n*⚡ कमांड:*\n/summary — पिछला सारांश फिर से भेजें\n/deepdive — गहराई से विश्लेषण\n/actionpoints — कार्य बिंदु\n/keyterms — मुख्य शब्द और शब्दावली\n/tone — स्वर और भावना विश्लेषण\n/clear — अपना सत्र साफ़ करें\n/reset — बॉट स्थिति को रीसेट करें\n/stats — उपयोग सांख्यिकी\n/language <नाम> — भाषा बदलें\n/languages — सभी समर्थित भाषाएँ\n\n*🌐 भाषाएँ:* EN · HI · KN · TA · TE · MR\nबदें: `Summarize in Hindi` या `/language kannada`"
    },
    "te": {
        "welcome": "👋 *స్వాగతం, {name}!*\n\nYouTube కోసం మీ వ్యక్తిగత AI పరిశోధన సహాయకుడు:\n\n🎥 ఏదైనా YouTube లింక్‌ని పంపండి → నిర్మాణాత్మక సారాంశం\n💬 తదుపరి ప్రశ్నలు అడగండి → ఆధారిత సమాధానాలు\n🌐 బహుభాషా — EN, HI, KN, TA, TE, MR\n🔬 లోతైన విశ్లేషణ, 🔑 ముఖ్య నిబంధనలు, 🎭 స్వరం విశ్లేషణ\n\n*కమాండ్లు:*\n/summary · /deepdive · /actionpoints\n/keyterms · /tone · /clear · /stats\n/language · /languages · /help\n\nప్రారంభించడానికి ఒక YouTube లింక్‌ని పంపండి 🚀",
        "help": "📖 *YouTube AI బాట్ — కమాండ్ గైడ్*\n\n*📥 ఇన్పుట్:*\nసారాంశం పొందడానికి ఏదైనా YouTube URLని పంపండి\n\n*❓ Q&A:*\nవీడియో లోడ్ అయిన తర్వాత ఏదైనా అడగండి\n\n*⚡ కమాండ్లు:*\n/summary — చివరి సారాంశాన్ని మళ్ళీ పంపు\n/deepdive — లోతైన విశ్లేషణ\n/actionpoints — కార్యాచరణ అంశాలు\n/keyterms — ముఖ్య నిబంధనలు & పదకోశం\n/tone — స్వరం & సెంటిమెంట్ విశ్లేషణ\n/clear — మీ సెషన్‌ను క్లియర్ చేయండి\n/reset — బాట్ స్థితిని రీసెట్ చేయండి\n/stats — వినియోగ గణాంకాలు\n/language <పేరు> — భాషను మార్చండి\n/languages — అన్ని మద్దతు ఉన్న భాషలు\n\n*🌐 భాషలు:* EN · HI · KN · TA · TE · MR\nమార్చండి: `Summarize in Hindi` లేదా `/language kannada`"
    }
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = MESSAGES.get(lang, MESSAGES["en"])
    text = msgs["welcome"].format(name=user_name)
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = MESSAGES.get(lang, MESSAGES["en"])
    await update.message.reply_text(msgs["help"], parse_mode="Markdown")


async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = language_service.list_supported_languages()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        current = session_store.get_language(user_id)
        lang_name = language_service.get_display_name(current)
        await update.message.reply_text(
            f"🌐 Current language: *{lang_name}*\n"
            f"Usage: `/language hindi`\nType /languages to see all options.",
            parse_mode="Markdown",
        )
        return

    lang_word = args[0].lower()
    lang_code = SUPPORTED_LANGUAGES.get(lang_word)
    if not lang_code:
        await update.message.reply_text(
            f"❌ Unknown language: *{args[0]}*\n"
            f"Supported: {', '.join(sorted(set(SUPPORTED_LANGUAGES.keys())))}",
            parse_mode="Markdown",
        )
        return

    session_store.set_language(user_id, lang_code)
    lang_name = language_service.get_display_name(lang_code)
    
    switch_msgs = {
        "en": f"✅ Language switched to *{lang_name}*!",
        "hi": f"✅ भाषा बदलकर *{lang_name}* कर दी गई है!",
        "te": f"✅ భాష *{lang_name}* కు మార్చబడింది!",
    }
    msg = switch_msgs.get(lang_code, switch_msgs["en"])
    
    await update.message.reply_text(msg, parse_mode="Markdown")

    # If a video is active, regenerate summary
    session = session_store.get_session(user_id)
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
                language=lang_code
            )
            session.summary = summary.text
            session_store.save_session(session)
            await update.message.reply_text(
                summary.text,
                parse_mode="Markdown",
                reply_markup=build_quick_actions_keyboard(lang_code)
            )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    if not session.summary:
        await update.message.reply_text(
            "📭 No summary yet. Send a YouTube link first!"
        )
        return
    await update.message.reply_text(
        session.summary,
        parse_mode="Markdown",
        reply_markup=build_quick_actions_keyboard(session.language),
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the user's current session and start fresh."""
    user_id = update.effective_user.id
    session_store.clear_session(user_id)
    await update.message.reply_text(
        "🗑 *Session cleared!*\nYour history has been wiped. Send a new YouTube link to start fresh.",
        parse_mode="Markdown",
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for /clear to reset the bot state."""
    return await clear_command(update, context)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot usage statistics."""
    stats = session_store.get_stats()
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"🎥 Videos processed: *{stats.get('videos_processed', 0)}*\n"
        f"💬 Questions answered: *{stats.get('questions_answered', 0)}*\n"
        f"👥 Active sessions: *{stats.get('active_sessions', 0)}*\n"
        f"📦 Cached transcripts: *{stats.get('cached_videos', 0)}*\n\n"
        f"⚡ _Powered by Groq LLaMA_",
        parse_mode="Markdown",
    )


UI_MESSAGES = {
    "en": {
        "generating_deepdive": "🔬 _Generating deep analysis..._",
        "generating_actionpoints": "📋 _Extracting action points..._",
        "generating_keyterms": "🔑 _Extracting key terms..._",
        "analysing_tone": "🎭 _Analysing tone..._",
        "no_video": "📭 No video loaded. Send a YouTube link first!",
    },
    "hi": {
        "generating_deepdive": "🔬 _गहरा विश्लेषण उत्पन्न किया जा रहा है..._",
        "generating_actionpoints": "📋 _कार्य बिंदु निकाले जा रहे हैं..._",
        "generating_keyterms": "🔑 _मुख्य शब्द निकाले जा रहे हैं..._",
        "analysing_tone": "🎭 _स्वर का विश्लेषण किया जा रहा है..._",
        "no_video": "📭 कोई वीडियो लोड नहीं है। पहले एक YouTube लिंक भेजें!",
    },
    "te": {
        "generating_deepdive": "🔬 _లోతైన విశ్लेషణ రూపొందించబడుతోంది..._",
        "generating_actionpoints": "📋 _కార్యాచరణ పాయింట్లు సేకరించబడుతున్నాయి..._",
        "generating_keyterms": "🔑 _ముఖ్య నిబంధనలు సేకరించబడుతున్నాయి..._",
        "analysing_tone": "🎭 _స్వరం విశ్లేషించబడుతోంది..._",
        "no_video": "📭 వీడియో ఏదీ లోడ్ కాలేదు. మొదట ఒక YouTube లింక్‌ను పంపండి!",
    },
}


async def deepdive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = UI_MESSAGES.get(lang, UI_MESSAGES["en"])

    if not session.transcript:
        await update.message.reply_text(msgs["no_video"])
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(msgs["generating_deepdive"], parse_mode="Markdown")

    from services.analysis import AnalysisService
    svc = AnalysisService()
    result = svc.deep_dive(session.video_title or "Video", session.transcript, session.language)
    await update.message.reply_text(result, parse_mode="Markdown")


async def actionpoints_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = UI_MESSAGES.get(lang, UI_MESSAGES["en"])

    if not session.transcript:
        await update.message.reply_text(msgs["no_video"])
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(msgs["generating_actionpoints"], parse_mode="Markdown")

    from services.analysis import AnalysisService
    svc = AnalysisService()
    result = svc.action_points(session.video_title or "Video", session.transcript, session.language)
    await update.message.reply_text(result, parse_mode="Markdown")


async def keyterms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /keyterms — extract key terms & glossary from the video."""
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = UI_MESSAGES.get(lang, UI_MESSAGES["en"])

    if not session.transcript:
        await update.message.reply_text(msgs["no_video"])
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(msgs["generating_keyterms"], parse_mode="Markdown")

    from services.keyterms import KeyTermsService
    svc = KeyTermsService()
    result = svc.extract(session.video_title or "Video", session.transcript, session.language)
    await update.message.reply_text(result, parse_mode="Markdown")


async def tone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tone — analyse video tone and sentiment."""
    user_id = update.effective_user.id
    session = session_store.get_session(user_id)
    lang = session.language or "en"
    msgs = UI_MESSAGES.get(lang, UI_MESSAGES["en"])

    if not session.transcript:
        await update.message.reply_text(msgs["no_video"])
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(msgs["analysing_tone"], parse_mode="Markdown")

    from services.sentiment import SentimentService
    svc = SentimentService()
    result = svc.analyse(session.video_title or "Video", session.transcript, session.language)
    await update.message.reply_text(result, parse_mode="Markdown")
