---
name: youtube-summarizer
description: >
  Summarize YouTube videos and answer questions about their content.
  Supports English and Indian languages (Hindi, Kannada, Tamil, Telugu, Marathi).
  Fetches transcripts, generates structured summaries with key points and timestamps,
  and allows contextual Q&A grounded in the video transcript.

triggers:
  - pattern: "https?://(www\\.)?(youtube\\.com|youtu\\.be)/\\S+"
    description: "Triggered when user sends a YouTube URL"

commands:
  - name: summary
    description: "Re-send the last video summary"
  - name: deepdive
    description: "Generate an in-depth analysis of the current video"
  - name: actionpoints
    description: "Extract actionable takeaways from the current video"
  - name: language
    args: "<language>"
    description: "Switch response language (english, hindi, kannada, tamil, telugu, marathi)"
  - name: languages
    description: "List all supported languages"

examples:
  - input: "https://youtube.com/watch?v=dQw4w9WgXcQ"
    output: "Generates structured summary with key points, timestamps, and core takeaway"
  - input: "What did they say about pricing?"
    output: "Answers grounded in transcript context"
  - input: "Summarize in Hindi"
    output: "Re-generates response in Hindi"
  - input: "/actionpoints"
    output: "Extracts actionable tips and steps from the video"
---

# YouTube Summarizer Skill for OpenClaw

This skill enables the OpenClaw AI agent to:

1. **Receive YouTube URLs** from users via Telegram
2. **Fetch transcripts** using youtube-transcript-api (no API key needed)
3. **Generate structured summaries** with key points, timestamps, and core insights
4. **Answer follow-up questions** grounded in the transcript (no hallucination)
5. **Support multiple languages**: English, Hindi, Kannada, Tamil, Telugu, Marathi

## Setup

```bash
# Install Python dependencies
cd /path/to/telegram_bot
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and GROQ_API_KEY

# Start the bot
python -m bot.main
```

## Integration with OpenClaw

OpenClaw routes Telegram messages through its gateway to this skill.
The bot handles transcript fetching and LLM summarization internally.

### OpenClaw Configuration (~/.openclaw/openclaw.json)
```json
{
  "model": {
    "provider": "groq",
    "name": "llama-3.3-70b-versatile"
  },
  "channels": {
    "telegram": {
      "token": "YOUR_TELEGRAM_BOT_TOKEN",
      "userId": "YOUR_TELEGRAM_USER_ID"
    }
  }
}
```

## Architecture

```
Telegram User
    ↓
OpenClaw Gateway (port 18789)
    ↓
Python Bot (python-telegram-bot)
    ├── TranscriptService → youtube-transcript-api
    ├── SummarizerService → Groq Llama 3
    ├── QAService → Groq Llama 3
    ├── LanguageService → Groq translation
    └── SessionStore → in-memory + cache
```
