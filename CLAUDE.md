# Daily-News project guidelines

This repo is a **Routine-driven daily tech-report pipeline**. Reports are generated as HTML in `reports/` and auto-merged to `main` by `.github/workflows/auto-merge-report.yml`. Once on `main`, the report is published immediately. There is **no human review in the loop** — the harness must catch mistakes before they ship.

## Hard rules (enforced by hooks — exit 2 on violation)

| Rule | Why |
|---|---|
| Report filename MUST be `reports/tech-report-YYYY-MM-DD.html` | The auto-merge workflow only picks up files matching this glob. Other names are silently dropped. |
| Report MUST be larger than 2048 bytes | Catches truncation, empty stub output, or generation failures. |
| Report body MUST contain its own date (`YYYY-MM-DD` or `YYYY年M月D日`) | Catches date mismatches (e.g. yesterday's content saved under today's filename). |
| No secret patterns (Stripe / GitHub PAT / OpenAI / Anthropic / AWS / Google / PEM / JWT) | API responses sometimes contain trace IDs that look like tokens. Real keys must never land in a public report. |

To bypass secret-scan for a legitimate fixture, add the literal string `SECRET-SCAN-OK` on that line.

## Generation rules

- **One report per day**. Do not overwrite a previous day's file.
- Reports have **4 sections**: 01 国内IT・DX / 02 AI / 03 AWS / 04 セキュリティ. All 4 must be present in every report.
- The search query list in `prompt/routine-prompt.md` includes cybersecurity queries — do not skip them.
- **Critical vulnerabilities are mandatory.** Anything with CVSS ≥ 9.0, a CISA KEV listing, an emergency vendor patch, confirmed in-the-wild exploitation, or unauthenticated remote exploitability MUST be included and placed first in the security section — never dropped for space. Include CVE number, CVSS score, affected versions, and the fixed version in the description.
- Target **3+ security cards** per report (and 2+ per other section). If you fall short, re-check the RSS feeds and remaining search queries before finalizing — but never pad with items older than 24 hours.
- 窓の杜 (`forest.watch.impress.co.jp`) and Impress Watch (`www.watch.impress.co.jp`) are **different sites**. 窓の杜 is a primary source for software vulnerability and emergency-patch coverage; check it for the security section.
- Report which RSS feeds succeeded or failed in the session output. If every Japanese security feed fails, backfill with site-scoped searches rather than filling the section with English-only sources.
- Cite sources with real working URLs. Broken links erode trust. Before committing, re-verify every card's URL, title, and publication date against the fetched page (see 手順4 in `prompt/routine-prompt.md`).
- Do not repeat a story already covered in the previous day's report — read the most recent existing report first and skip duplicates unless there are genuinely new developments.
- Prefer RSS feeds (exact `pubDate`) over search-result summaries when determining publication dates — the feed list is in `prompt/routine-prompt.md`.
- `card-date` is the **publication date of the source article or announcement page**, not the original product announcement date. If a feature was announced days ago but a new article covering it was published today, use today's article date. The hook enforces `card-date ≥ prev_day (report date − 1)`.
- Do not paste raw API responses or request IDs into the report. Summarize, don't dump.
- Keep the HTML self-contained: inline CSS, no external JS dependencies. The report should render correctly when shared as a single file.
- The date in the title/heading must match the filename date — the hook will reject mismatches.

## Workflow

- Push to a `claude/**` branch. The `auto-merge-report.yml` workflow handles syncing to `main`.
- **Never push directly to `main`**. Anything on `main` is published immediately with no review, so accidental main commits go public.
- After your push, check the Actions tab to confirm the workflow succeeded. If the auto-merge silently no-ops, the filename probably doesn't match.
- The auto-merge workflow re-runs the report validations (size / date / sections / card-dates / secrets) server-side before syncing. Every `card-date` must be within `report date − 1 .. report date`. If validation fails, the report does NOT reach main — fix the report and push again.
- After a successful sync, the source `claude/**` branch is **auto-deleted** and `reports.json` (used by index.html) is regenerated on main.
- `report-watchdog.yml` runs at 09:00 JST daily and files an issue if today's report is missing from main.
- **Non-report changes** (prompt, hooks, CLAUDE.md, index.html) are NOT synced by auto-merge. Open a separate PR to merge them to main.

## API-based generation (`daily-report.yml`)

An alternative to the claude.ai Routine that runs on GitHub Actions with the Anthropic API (pay-as-you-go), so the pipeline does not depend on a claude.ai subscription.

- Runs daily at 06:00 JST (and on manual dispatch). `scripts/fetch_rss.py` pre-fetches the RSS feeds and filters them by publication time into `rss-digest.md`; Claude then runs `prompt/ci-overrides.md` + `prompt/routine-prompt.md` with a restricted tool set (no git, no arbitrary shell).
- Mode is set by the repository variable `DAILY_REPORT_MODE`: `dry-run` (default) only uploads the report as an artifact; `publish` pushes it to a `claude/daily-report-*` branch so `auto-merge-report.yml` validates and syncs it as usual.
- Secrets: `ANTHROPIC_API_KEY` (the job skips itself when unset) and `GH_PAT` (required for `publish` — pushes made with `GITHUB_TOKEN` do not trigger other workflows). Optional variable: `DAILY_REPORT_MODEL` (default `claude-sonnet-5`).
- In `publish` mode the job exits before calling the API if today's report already exists on main, so running it alongside the Routine never produces two reports.
- The API cost of each run is shown in the job summary and in the uploaded execution log.

## Prompts (`prompt/`)

- Treat changes here as code changes. Small focused diffs. The commit body explains *why* the prompt is changing — what behavior you're trying to improve or fix.
- Test prompt changes on a single branch before letting the Routine pick them up.
- `ci-overrides.md` overrides specific steps of `routine-prompt.md` for the Actions run (RSS digest instead of fetching feeds, a reduced search list, no git). When you change a step it overrides, check that both files still agree.
- The RSS feed list exists in two places: `routine-prompt.md` (手順2-1) and `FEEDS` in `scripts/fetch_rss.py`. Keep them in sync.

## What NOT to do

- Don't disable or modify hooks to "make it work" — fix the actual problem.
- Don't commit `.env` files. The secret-scan hook ignores gitignored paths, but committing them anyway is still a leak.
- Don't push placeholder / "test" content to a `claude/**` branch — it will auto-merge and go public on `main`.


## Dependency updates (Dependabot)

Dependabot opens a PR immediately whenever a dependency has a published vulnerability, and once a week opens one grouped PR of minor/patch updates per package directory (each release held 5 days first). Patch and minor PRs merge automatically once every other check on the PR passes; major updates, and any PR whose checks fail, stay open for manual handling.

- When asked to handle an open Dependabot PR, read the changelog for breaking changes, adapt the code, and get the checks green. Security PRs are priority work — each open one is a known vulnerability in production.
- `.github/dependabot.yml` is generated: after adding a package directory, re-run `./install.sh add . --with dependabot` instead of editing it.
- Never add `ignore:` rules to it: Dependabot applies `ignore` to security updates too, so it would silently block vulnerability fixes. To stop a version update, close its PR or use `allow`.
- Auto-merge is only as safe as the checks behind it. When adding features, add tests — they are what stops a bad update from shipping unattended.

### Daily-News specifics

- **CI (`ci.yml`) is the gate.** It runs on every PR: `actionlint` (with shellcheck) over all workflows, `tests/test_fetch_rss.py`, and `tests/test_hooks.sh` (the report-validation hooks must accept a valid report and reject broken ones). Dependabot PRs auto-merge only after these pass. If you change `scripts/fetch_rss.py` or `.claude/hooks/*`, update the tests in the same PR.
- **Actions are pinned to full commit SHAs** with the version as a trailing comment (`uses: actions/checkout@<sha> # v4.4.0`). Keep that format for any new `uses:` line — it is what lets Dependabot propose patch/minor bumps, and it stops a moved tag from swapping the code that runs.
- **Merging needs the Dependabot secret `DEPENDABOT_MERGE_TOKEN`.** Every Dependabot PR here edits `.github/workflows/`, which `GITHUB_TOKEN` can never merge. Use a fine-grained PAT limited to this repository with Contents, Pull requests and Workflows set to read/write, stored under Settings → Secrets and variables → **Dependabot** (Actions secrets are not visible to Dependabot runs). Without it the auto-merge job fails fast and the PR waits for a human.
- `dependabot-automerge.yml` is customized for the token above. Re-running `install.sh add . --with dependabot` overwrites it (keeping a `.bak`) — re-apply the change afterwards.
