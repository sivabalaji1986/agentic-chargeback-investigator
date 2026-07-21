# Commit Log

## 2026-07-21 — Ignore Node.js build artifacts

**Files:** `.gitignore`
**What:** Added `node_modules/`, `*.tsbuildinfo`, and the `tsc`-emitted `investigator-ui/vite.config.js` / `investigator-ui/vite.config.d.ts` to `.gitignore`.
**Why:** Running `npm run build` in `investigator-ui/` for the first time (Task 7) installs `node_modules/` and, because `tsconfig.node.json` is a composite project referenced via `tsc -b`, emits `.tsbuildinfo` cache files and a compiled `vite.config.js`/`.d.ts` alongside the TypeScript source; none of these are meant to be committed.

## 2026-07-21 — Fix investigator-ui PostCSS config for Tailwind v4

**Files:** `investigator-ui/postcss.config.js`, `investigator-ui/package.json`, `investigator-ui/package-lock.json`
**What:** Swapped the PostCSS plugin entry from `tailwindcss` to `@tailwindcss/postcss` (added as a devDependency pinned to `4.3.2`, matching the installed `tailwindcss` version) after `npm run build` failed with "It looks like you're trying to use `tailwindcss` directly as a PostCSS plugin."
**Why:** Tailwind CSS v4 moved its PostCSS integration into a separate `@tailwindcss/postcss` package; the app shell's `postcss.config.js` still referenced the old v3-style plugin name, which broke the first real `vite build`.

## 2026-07-21 — Add git-commit skill

**Files:** `.claude/skills/git-commit/SKILL.md`
**What:** Added the git-commit skill, tailored for this Python repo (Python-specific never-stage list, repo name, commit workflow).
**Why:** Give Claude Code a repo-specific, repeatable procedure for committing changes and logging them in docs/COMMIT_LOG.md.

## 2026-07-21 — Add use-case tech summary

**Files:** `docs/use-case-tech-summary.md`
**What:** Added the canonical design reference covering project overview, tech stack, architecture components, specialist agents, responsibility matrix, investigation flow, decision rules, demo scenarios, repository structure, and key architectural principles.
**Why:** Provide a single source of truth for the agentic chargeback investigator design (A2A, MCP, RAG, AG-UI, A2UI) before implementation begins.

## 2026-07-21 — Add project README

**Files:** `README.md`
**What:** Added a README with the project title.
**Why:** Establish a starting point for project documentation.

## 2026-07-21 — Ignore macOS .DS_Store files

**Files:** `.gitignore`
**What:** Added `.DS_Store` to the ignore list.
**Why:** Prevent macOS Finder metadata files from being tracked.
