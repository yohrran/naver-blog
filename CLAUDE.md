# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (skips if today's draft already exists)
python -m src.main

# Run and overwrite existing drafts
python -m src.main --overwrite
```

There is no test suite. The pipeline can be manually verified by running it with real API keys in `.env`.

## Architecture

A linear 4-stage pipeline that runs daily via GitHub Actions (09:00 KST):

```
collect_news() + collect_youtube()   →   format_draft()   →   save_draft()   →   send_draft_email()
src/collectors/                           src/formatter/        src/output/        src/output/
```

`src/main.py` orchestrates the pipeline. Each stage is fully isolated and communicates only through plain Python dicts:

- **Collectors** return lists of dicts (`title`, `description`, `link`, etc.)
- **Formatter** returns `{"date": str, "markdown": str, "html": str}`
- **Output modules** consume the formatter dict independently

## Key files

- `src/config.py` — **single source of truth** for all behavior: search keywords (`NEWS_KEYWORDS`), topic classification rules (`TOPIC_KEYWORDS`), YouTube channel IDs (`YOUTUBE_CHANNEL_IDS`), articles-per-topic cap (`MAX_ARTICLES_PER_TOPIC`), and the `drafts/` output path. All customization goes here.
- `drafts/` — generated output files named `YYYY-MM-DD.md` and `YYYY-MM-DD.html`. Auto-committed by GitHub Actions.
- `.github/workflows/daily-blog.yml` — cron schedule (UTC) and the 5 required GitHub Secrets.

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
NAVER_CLIENT_ID, NAVER_CLIENT_SECRET   # Naver Search API
YOUTUBE_API_KEY                         # YouTube Data API v3
GMAIL_ADDRESS, GMAIL_APP_PASSWORD       # Gmail (App Password, not account password)
```

Missing API keys are handled gracefully: the relevant collector logs a warning and returns an empty list, allowing the pipeline to continue with partial data.
