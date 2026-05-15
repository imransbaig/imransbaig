# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`fastclose-backend` — a minimal Node.js/Express server for the "FastClose AI accounting solution". The codebase currently consists of a single `server.js` exposing `GET /` and `GET /health`. There is no build step, no test framework, and no linter configured; `typescript` is listed as a devDependency but no `.ts` files exist.

## Commands

- `npm install` — install dependencies (only `express`).
- `npm start` — runs `node server.js`. Server listens on `process.env.PORT` (default `3000`).

There is no `test`, `build`, or `lint` script. If asked to add tests/linting, surface that there is no existing harness rather than assuming one.

## Deployment

Two GitHub Actions workflows in `.github/workflows/` both deploy to **Azure Static Web Apps** on push/PR to `master`:

- `azure-static-web-apps-gentle-flower-073b5ef0f.yml` — the active Azure-managed workflow (uses OIDC + `AZURE_STATIC_WEB_APPS_API_TOKEN_GENTLE_FLOWER_073B5EF0F`).
- `staticwebapp.yml` — an older/duplicate workflow that references `AZURE_STATIC_WEB_APPS_API_TOKEN` and has a stray trailing `x` on line 35 (likely a typo, but harmless YAML-wise since it's outside any block — leave it unless asked).

Note the mismatch: this is a Node/Express **backend** but it is being deployed as a **static** web app (`app_location: "/"`, `api_location: ""`). The Express server is not actually invoked by the Azure SWA deployment. If a task involves the deployed site, clarify the user's intent before changing workflows.

## Repository quirks

- **`index.html` is not HTML.** It is a binary Microsoft Word 2007+ (`.docx`) file mis-named with an `.html` extension (`file` reports `Microsoft Word 2007+`). Do not try to read or edit it as text. If a task requires its contents, ask the user before converting or renaming.
- **`desktop.ini`** is a Windows Explorer metadata file and should generally be left alone (consider adding to `.gitignore` if asked to clean up).
- `node_modules/` is committed to the repo.

## Branch policy for this session

Per the session instructions, develop on `claude/add-claude-documentation-SSgk2`, commit with descriptive messages, and push with `git push -u origin <branch>` (retry with exponential backoff on network errors). Do not open a PR unless explicitly asked.
