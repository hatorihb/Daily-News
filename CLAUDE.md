# Daily-News project guidelines

This repo is a **Routine-driven daily tech-report pipeline**. Reports are generated as HTML in `reports/` and auto-merged to `main` by `.github/workflows/auto-merge-report.yml`. After merge, `tweet-report.yml` tweets the URL. There is **no human review in the loop** — the harness must catch mistakes before they ship.

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
- The search query list in `prompt/routine-prompt.md` includes a cybersecurity query — do not skip it.
- Cite sources with real working URLs. Broken links erode trust. If a URL is critical, sanity-check it before pasting.
- `card-date` is the **publication date of the source article or announcement page**, not the original product announcement date. If a feature was announced days ago but a new article covering it was published today, use today's article date. The hook enforces `card-date ≥ prev_day (report date − 1)`.
- Do not paste raw API responses or request IDs into the report. Summarize, don't dump.
- Keep the HTML self-contained: inline CSS, no external JS dependencies. The report should render correctly when shared as a single file.
- The date in the title/heading must match the filename date — the hook will reject mismatches.

## Workflow

- Push to a `claude/**` branch. The `auto-merge-report.yml` workflow handles syncing to `main`.
- **Never push directly to `main`**. The tweet workflow fires on merge, so accidental main commits become public.
- After your push, check the Actions tab to confirm the workflow succeeded. If the auto-merge silently no-ops, the filename probably doesn't match.
- The auto-merge workflow re-runs the report validations (size / date / sections / secrets) server-side before syncing. If it fails, the report does NOT reach main — fix the report and push again.
- After a successful sync, the source `claude/**` branch is **auto-deleted** and `reports.json` (used by index.html) is regenerated on main.
- `report-watchdog.yml` runs at 09:00 JST daily and files an issue if today's report is missing from main.
- **Non-report changes** (prompt, hooks, CLAUDE.md, index.html) are NOT synced by auto-merge. Open a separate PR to merge them to main.

## Prompts (`prompt/`)

- Treat changes here as code changes. Small focused diffs. The commit body explains *why* the prompt is changing — what behavior you're trying to improve or fix.
- Test prompt changes on a single branch before letting the Routine pick them up.

## What NOT to do

- Don't disable or modify hooks to "make it work" — fix the actual problem.
- Don't commit `.env` files. The secret-scan hook ignores gitignored paths, but committing them anyway is still a leak.
- Don't push placeholder / "test" content to a `claude/**` branch — it will auto-merge and tweet.
