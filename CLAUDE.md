# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Literature-tracker is an automated academic-paper pipeline (Python, no web server). It pulls 50+ journal RSS feeds (Nature/Science/APS/ACS/Wiley/RSC/Elsevier/arXiv), filters for ML × ferroelectric/condensed-matter relevance, enriches with AI (Chinese translation, relevance scoring, deep full-text reads), and publishes Chinese daily/weekly digests to GitHub Pages. The entire pipeline runs on GitHub Actions cron — there is no daemon to run locally.

## Commands

```bash
# Tests — runs WITHOUT installing deps (stdlib-only fallback skips bs4/json_repair cases)
python3 run_tests.py                       # all top-level test_* functions
python3 run_tests.py test_focus_core.py    # specific module(s)

# Script-style tests (assertions live in main(), run each individually)
python3 test_daily_pages_render.py

# Full CI-equivalent run
pip install -r requirements.txt && python3 run_tests.py

# Pipeline entry points (normally invoked by Actions, not locally):
python3 run_optimized_sync.py              # fetch → AI relevance filter → zh enrich → notify
python3 generate_daily_pages.py --days 2   # build docs/daily/*.html (default: Beijing yesterday)
python3 run_deep.py                        # APS full-text deep read + arXiv enrich + posters
python3 weekly_summary.py                  # build docs/weekly/*.html
```

## Test conventions

New tests MUST be top-level `test_*` functions with no required args, using `unittest.mock` + `tempfile` — NOT pytest fixtures (`monkeypatch`, `tmp_path`). This lets `run_tests.py` execute them locally (no pytest needed) and CI execute them under pytest. Script-style `main()` tests are legacy; smoke.yml runs them one at a time. `smoke.yml` enforces `py_compile` + `run_tests.py` + the script tests on every push/PR.

## Architecture

Data flows one direction through a single source of truth:

```
RSS feeds ──run_optimized_sync.py──▶ data/  (history.json, index.json, ai_relevant_*, deep caches)
                                       │
                                       ├─▶ articles/*.md           (one file per paper, date_hash named)
                                       ├─▶ generate_daily_pages.py ─▶ docs/daily/*.html
                                       ├─▶ run_deep.py             ─▶ data/aps_*.json, docs/images/posters/
                                       └─▶ weekly_summary.py       ─▶ docs/weekly/*.html
```

- `data/` is the **only** authoritative store. Everything else regenerates from it.
- `docs/` is the GitHub Pages site (SPA: index.html + app.js, virtual scroll / IndexedDB / inverted-index search / PWA). `docs/daily`, `docs/weekly`, `docs/images` are generated artifacts.
- **`docs/data/` is NOT committed.** The deploy job copies `data/*` → `docs/data/` at publish time only. Do not commit `docs/data/` or read it as a source — always read from `data/`.

### Key modules

- `focus_filter.py` / `focus_core.py` — keyword/relevance gating (the "is this paper on-topic?" logic). `analyze_focus`, `is_daily_focus`, `is_target_domain`, `is_hard_offtopic`, `core_score`. Tune relevance behavior here.
- `ai_summarizer.py` — AI provider abstraction. `AIProvider` ABC with `GeminiProvider`, `KimiClaudeCodeProvider`, `OpenRouterProvider`; `build_provider(provider, api_key, model)` is the factory. Add new providers here.
- `relevance_enricher.py` — batch AI relevance scoring; `zh_enricher.py` / `translator.py` — Chinese translation.
- `run_deep.py` — orchestrates APS full-text fetch → deep read → poster → classify. **Idempotent**: papers already carrying a complete `deep_analysis` in `data/aps_<date>.json` are reused, never re-sent to the model. Completion is gated by `_deep_complete` / `_tier2_complete` (`ft_attempts` caps retries at 3 to protect the AI budget).
- `data_manager.py` — owns history/index JSON and per-article markdown. `deduplicator.py` — title-similarity dedup (threshold 0.98).

### Timezone rule

The pipeline reports on **Beijing time yesterday**. Actions fire at UTC 0:00/12:00 (Beijing 08:00/20:00), so summarizing "yesterday" captures a full day. Preserve this offset when touching date logic.

## GitHub Actions

| Workflow | Trigger (UTC) | Purpose |
|---|---|---|
| fetch.yml | 00:00, 12:00 + manual | fetch → filter → enrich → daily, commit + self-deploy |
| generate-deep.yml | 03:30 + manual | APS/arXiv deep read, posters, re-render daily |
| weekly-summary.yml | Sun 01:00 + manual | weekly digest (01:00 is deliberate off-peak — do not move to 00:00) |
| deploy-on-push.yml | push main | Pages deploy for non-auto-commit pushes |
| smoke.yml | push/PR | py_compile + run_tests.py + script tests |
| backfill-daily / -weekly / -zh, test.yml | manual | history backfill / RSS connectivity check |

Engineering invariants are pinned by `test_actions.py` (shallow clone `fetch-depth:1`, push must carry 5× rebase-retry since parallel workflows push to main, deploy copies `docs/data` before upload, all jobs have timeouts, crons don't collide). Changing a workflow without updating `test_actions.py` will fail smoke.

## Config

- `config.py` — RSS feeds, `USER_KEYWORDS` (per-user keyword sets), email, dedup/focus thresholds.
- `config.local.py` — secrets, gitignored (copy from `config.local.py.example`).
- CI secrets / env: `AI_PROVIDER`/`AI_MODEL`/`AI_API_KEY`/`AI_BASE_URL`, `KIMI_*`, `NOTION_*`, `TG_LIT_*`, `APS_HTTP_*` (private full-text source). Config reads `config.local.py` first, then env vars.
- See `README_CONFIG.md` and `DEPLOYMENT_GUIDE.md` for details.

## Notes

- Pipeline steps fail silently and degrade — a missing AI key falls back to heuristic relevance, AI digest failures fall back to a list-style daily page. Don't add hard failures to these paths.
- Design specs live in `.kiro/specs/`; historical build summaries in `archive/` (read-only reference).
