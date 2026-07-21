---
name: git-commit
description: Commit changes for the agentic-chargeback-investigator project with a detailed commit message and an entry in docs/COMMIT_LOG.md. Use when the user asks to commit or save changes.
argument-hint: "[optional commit message]"
---

# Commit Changes — agentic-chargeback-investigator

This repo (`sivabalaji1986/agentic-chargeback-investigator`) commits directly
to `main` — there is no branch-per-issue or PR workflow here. Do not create
branches or PRs unless the user explicitly asks for one.

## Current state
!`git status --short`

## Recent commits for style reference
!`git log --oneline -5`

## Staged and unstaged diff
!`git diff HEAD`

## Steps

### 1. Identify what to commit

Review the changed files above. Never stage:
- `.env`, `.envrc`, or any file containing real credentials/secrets
- `__pycache__/`, `*.pyc` — bytecode
- `.venv/`, `venv/`, `env/` — virtual environments
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/` — test/lint/coverage artifacts
- `*.egg-info/`, `build/`, `dist/` — packaging output
- Anything else already covered by `.gitignore`

Stage specific files by path — never `git add -A` or `git add .`.

### 2. Draft the commit message

If the user provided a message via `$ARGUMENTS`, use it as the subject line.
Otherwise derive one from the diff, using this repo's existing style (see
`git log` above — plain imperative subject lines, no type prefix is required
but conventional prefixes are fine if they read naturally: `feat:`, `fix:`,
`docs:`, `refactor:`, `test:`, `chore:`).

Format:
```
<short subject under 70 chars>

<body — 1-5 bullet points: what changed and why, not a restatement of the diff>
```

### 3. Append an entry to docs/COMMIT_LOG.md

Create `docs/COMMIT_LOG.md` if it doesn't exist yet, with a `# Commit Log` header.

Append one entry per commit, most recent first, directly below the header:

```markdown
## YYYY-MM-DD — <short subject line>

**Files:** `path/one.py`, `path/two.yaml`
**What:** <1-2 sentences on what changed>
**Why:** <1 sentence on the motivation — bug fix, new feature, design decision, etc.>
```

Use today's actual date. Keep each entry tight — this is a scannable log, not
prose documentation. Stage this file alongside the code changes in the same
commit.

### 4. Commit

```bash
git add <specific files> docs/COMMIT_LOG.md
git commit -m "$(cat <<'EOF'
<subject>

<body>

EOF
)"
```

### 5. Confirm

Report the commit hash and a one-line summary. Do **not** push to `origin`
unless the user explicitly asks — pushing is a separate, confirmed action per
this project's git safety rules.
