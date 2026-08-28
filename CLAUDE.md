# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (this machine has `pip3`, not `pip`)
pip3 install -r requirements.txt

# [1] Collect news → drafts/YYYY-MM-DD.{md,html}, email it
python -m src.main
python -m src.main --overwrite

# [2] Write a finished post → posts/YYYY-MM-DD-slug.md
python -m src.compose                       # from today's draft
python -m src.compose --date 2026-08-25
python -m src.compose --topic "any topic" --notes "..."

# [3] Fill the Naver editor (never publishes)
python -m src.publish --login               # once: log in by hand
python -m src.publish [path]
python -m src.publish --debug               # when selectors break
```

There is no test suite. Stages 1 and 2 need real API keys in `.env`; stage 3 needs a
saved Naver session and can only be verified by hand against the live editor.

## Architecture

Three independent stages. Only stage 1 runs on GitHub Actions (09:00 KST); stages 2 and 3
are run by hand.

```
[1] collect_news() + collect_youtube() → format_draft() → save_draft() → send_draft_email()
    src/collectors/                      src/formatter/    src/output/    src/output/

[2] load_draft_markdown() ─┐
    (or a --topic string)  ├→ write_from_draft()/write_from_topic() → save_post()
    src/output/            ┘  src/generator/post_writer.py            src/generator/post_file.py

[3] load_post() → open_and_fill() → (human clicks 발행)
    src/generator/  src/publisher/naver_editor.py
```

Every stage communicates only through plain Python dicts:

- **Collectors** return lists of dicts (`title`, `description`, `link`, etc.)
- **Formatter** returns `{"date": str, "markdown": str, "html": str}`
- **Generator** returns `{"title": str, "tags": [str], "body": str}`
- **Publisher** consumes the generator dict

This is why stage 2 could be added without touching stage 1: `save_draft()` and
`send_draft_email()` never knew about each other in the first place.

## Constraints that shape the design

- **Naver's blog write API was shut down in May 2020.** There is no official way to post
  programmatically. `naver.github.io/naver-openapi-guide/apilist.html` still lists
  `blog/writePost.json` — that page is stale; do not build against it.
- **Automated publishing risks account sanctions.** Naver blocks access outside "the range
  of physical human writing and registration". `src/publisher/` therefore fills the editor
  and stops. Do not add a click on the 발행 button.
- **Login is never automated.** `python -m src.publish --login` opens a browser, a human
  logs in, and only the resulting cookies are saved to `.naver_session.json` (gitignored,
  chmod 600). No credentials live in code or `.env`.
- **The Naver Search API is migrating to NAVER API HUB.** `openapi.naver.com` +
  `X-Naver-Client-Id/Secret` still works, but legacy support ends 2027-06-30; the
  replacement is `naverapihub.apigw.ntruss.com` + `X-NCP-APIGW-API-KEY-ID/KEY`.

## Key files

- `src/config.py` — **single source of truth** for all behavior: search keywords (`NEWS_KEYWORDS`), topic classification rules (`TOPIC_KEYWORDS`), YouTube channel IDs (`YOUTUBE_CHANNEL_IDS`), articles-per-topic cap (`MAX_ARTICLES_PER_TOPIC`), the Claude model, and all output paths. All customization goes here.
- `blog-post.md` — the writing-style exemplar. It is fed to Claude as a few-shot sample, so the post's tone *is* the blog's tone. Swapping this file changes the voice more than editing rules does.
- `src/generator/style.py` — explicit style rules (`STYLE_RULES`) plus prompt assembly. `build_system_prompt()` must stay deterministic — any varying value (timestamp, random ID) silently kills the prompt cache.
- `src/publisher/naver_editor.py` — the `SELECTORS` dict is the only thing that breaks when Naver changes the editor DOM. Fix it there; leave the rest alone.
- `drafts/` — collected raw material, `YYYY-MM-DD.{md,html}`. Auto-committed by GitHub Actions.
- `posts/` — finished posts, gitignored (a public repo shouldn't leak unpublished drafts).
- `.github/workflows/daily-blog.yml` — cron schedule (UTC) and the 5 required GitHub Secrets. It runs stage 1 only.

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
NAVER_CLIENT_ID, NAVER_CLIENT_SECRET   # Naver Search API
YOUTUBE_API_KEY                         # YouTube Data API v3
GMAIL_ADDRESS, GMAIL_APP_PASSWORD       # Gmail (App Password, not account password)
ANTHROPIC_API_KEY                       # Claude API — stage 2 only
NAVER_BLOG_ID                           # blog.naver.com/<this> — stage 3 only
```

Missing keys degrade rather than crash: a collector without keys logs a warning and returns
an empty list so stage 1 continues on partial data. Stages 2 and 3 fail fast with an
actionable message instead, since there is no partial result worth producing.
