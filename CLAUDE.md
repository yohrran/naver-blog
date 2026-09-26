# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (this machine has `pip3`, not `pip`)
pip3 install -r requirements-write.txt   # local: everything
pip3 install -r requirements.txt         # CI: collection only

# [1] Collect news → drafts/YYYY-MM-DD.{md,html}, email it
python -m src.main
python -m src.main --overwrite

# [2] Write a finished post → posts/YYYY-MM-DD-slug.md
python -m src.compose                       # from today's draft
python -m src.compose --date 2026-08-25
python -m src.compose --topic "any topic" --notes "..."

# [3] Build a copy-paste handoff page, open it, paste into Naver by hand
python -m src.handoff                       # latest post in posts/
python -m src.handoff [path]
python -m src.handoff --no-open             # write the file, don't open a browser
```

There is no test suite. Stages 1 and 2 need real API keys in `.env`. Stage 3 needs
neither keys nor a browser session — it only reads a post file and writes an HTML page —
so it is the one stage you can run and eyeball anywhere. What it cannot check for you is
how SmartEditor renders the pasted result; that is a human's look at the live editor.

## Architecture

Three independent stages. Only stage 1 runs on GitHub Actions (09:00 KST); stages 2 and 3
are run by hand.

```
[1] collect_news() + collect_youtube() → format_draft() → save_draft() → send_draft_email()
    src/collectors/                      src/formatter/    src/output/    src/output/

[2] load_draft_markdown() ─┐
    (or a --topic string)  ├→ write_from_draft()/write_from_topic() → save_post()
    src/output/            ┘  src/generator/post_writer.py            src/generator/post_file.py

[3] load_post() → save_handoff() → (human copies 3 times, clicks 발행)
    src/generator/  src/publisher/handoff_page.py
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
  of physical human writing and registration". Stage 3 therefore stops at the clipboard.
  Do not add browser automation that clicks 발행.
- **Browser automation was tried and removed (2026-08-29).** A Playwright path used to log
  in with a persistent Chrome profile and type the post into the editor. It broke on every
  editor DOM change, expired sessions silently, and spent ~14s per post typing into a
  contenteditable. It also could not press 발행 anyway, so it saved exactly one paste. If
  you are tempted to bring it back, read the next bullet first — the clipboard produces a
  *better* post, not merely an easier one.
- **Typing loses formatting; pasting keeps it.** SmartEditor ignores markdown, so a keyboard
  path must strip `##`, `**`, and `[]()` down to plain text (`editor_text.py` still does
  this for the [평문으로] fallback) and the human re-applies every heading and bold by hand.
  A clipboard carries `text/html`, so `handoff_page.py` pastes headings, bold, links, and
  lists intact.
- **The handoff page runs from `file://`, so it copies with `document.execCommand('copy')`.**
  Deprecated but functional, and unlike `ClipboardItem` it needs no secure context. It also
  copies a *selection*, which is what makes the browser attach `text/html` at all.
- **The Naver Search API is migrating to NAVER API HUB.** `openapi.naver.com` +
  `X-Naver-Client-Id/Secret` still works, but legacy support ends 2027-06-30; the
  replacement is `naverapihub.apigw.ntruss.com` + `X-NCP-APIGW-API-KEY-ID/KEY`.

## Key files

- `src/config.py` — **single source of truth** for all behavior: search keywords (`NEWS_KEYWORDS`), topic classification rules (`TOPIC_KEYWORDS`), YouTube channel IDs (`YOUTUBE_CHANNEL_IDS`), articles-per-topic cap (`MAX_ARTICLES_PER_TOPIC`), the Claude model, and all output paths. All customization goes here.
- `blog-post.md` — the writing-style exemplar. It is fed to Claude as a few-shot sample, so the post's tone *is* the blog's tone. Swapping this file changes the voice more than editing rules does.
- `src/generator/style.py` — explicit style rules (`STYLE_RULES`) plus prompt assembly. `build_system_prompt()` must stay deterministic — any varying value (timestamp, random ID) silently kills the prompt cache.
- `src/publisher/handoff_page.py` — builds the copy-paste page. Chrome serializes **computed** styles into the clipboard, so anything the copy source inherits lands in the Naver post — in dark mode that means a black background behind every paragraph. Two rules keep the clipboard clean, and both are easy to break by accident: (1) the styled `#preview` and the offscreen `#clip-body` are separate elements, and (2) the CSS reset is scoped `.wrap, .wrap *`, never a bare `*`. Restoring a global `*` rule puts `box-sizing` back on every pasted tag. `#clip-body` also pins `color-scheme: light` and an explicit white background; `transparent` is not enough, because Chrome then bakes in the ancestor's background instead. Verified by copying in both color schemes and pasting into a separate white page — pasting into the same page hides the leak, since Chrome omits styles that match the target.
- `src/publisher/markdown_html.py` — markdown → paste-ready HTML. Hand-rolled rather than a dependency: the posts only use 7 constructs. Paragraph line breaks become `<br>` deliberately — this blog's rhythm is one sentence per line, and standard markdown would collapse them.
- `src/publisher/editor_text.py` — markdown → plain text, stripped of every symbol. Only the [평문으로] button uses it now; it is the fallback for the day a pasted HTML lands badly.
- `drafts/` — collected raw material, `YYYY-MM-DD.{md,html}`. Auto-committed by GitHub Actions.
- `posts/` — finished posts, gitignored (a public repo shouldn't leak unpublished drafts).
- `.github/workflows/daily-blog.yml` — cron schedule (UTC) and the 5 required GitHub Secrets. It runs stage 1 only, so it installs the lean `requirements.txt`.
- `requirements.txt` / `requirements-write.txt` — split deliberately: stage 1 does not import `anthropic`, and CI shouldn't pay to install it daily. Stage 3 needs no third-party package at all. Keep new stage-2 deps out of `requirements.txt`.

## Environment variables

Copy `.env.example` to `.env` and fill in:

```
NAVER_CLIENT_ID, NAVER_CLIENT_SECRET   # Naver Search API
YOUTUBE_API_KEY                         # YouTube Data API v3
GMAIL_ADDRESS, GMAIL_APP_PASSWORD       # Gmail (App Password, not account password)
ANTHROPIC_API_KEY                       # Claude API — stage 2 only
```

Missing keys degrade rather than crash: a collector without keys logs a warning and returns
an empty list so stage 1 continues on partial data. Stages 2 and 3 fail fast with an
actionable message instead, since there is no partial result worth producing.
