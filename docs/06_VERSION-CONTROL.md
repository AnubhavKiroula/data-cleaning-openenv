# Version Control Guidelines — data-cleaning-openenv

> **For AI coding tools:** When asked to commit, always follow the Conventional Commits format in Section 2. Never suggest committing more than 1–2 logical file changes at once. Always suggest branching per Section 3 before writing new-feature code, and draft a PR description per Section 4 template when a branch is ready.

---

## 1. Why This Matters

- **Clean commit history** = easier debugging, easier code review, and a traceable record of every decision.
- **Frequent small commits > rare giant commits** — easier to revert, easier to review, easier to understand *why* a change was made.
- **Branch discipline** = parallel work without stepping on each other, and a stable `main` that's always deployable.

---

## 2. Commit Message Format (Conventional Commits)

**Format:**
```
<type>: <short summary in present tense, under 50 chars>

<optional body — only if the change is non-trivial>
<reference to docs file or SRS edge case if applicable>
```

### Allowed types

| Type | Use for |
|---|---|
| `feat` | A new feature or API endpoint |
| `fix` | Bug fix |
| `refactor` | Code restructuring with no behaviour change |
| `chore` | Maintenance — deps, config, formatting, non-code housekeeping |
| `docs` | Documentation-only changes (including `docs/` files) |
| `test` | Adding or updating tests |
| `style` | Formatting/whitespace/naming, no logic change |
| `perf` | Performance improvement |
| `ci` | CI pipeline/workflow changes |
| `build` | Build system changes (Dockerfile, docker-compose, requirements.txt) |
| `revert` | Reverting a previous commit |

### Examples

**New endpoint:**
```
feat: add GET /api/results/{id}/download endpoint

Returns the cleaned CSV file as a FileResponse.
Refs: 02_SRS.md FR-10
```

**Bug fix:**
```
fix: prevent division by zero in quality score when dataset has zero rows

Refs: 02_SRS.md edge case #2
```

**CI change:**
```
ci: add pull-requests write permission to build-and-publish workflow

Required for the PR comment step (actions/github-script) to post
image refs on PR events without a 403.
```

**Docs change:**
```
docs: add PHASE-2-COMPLETION implementation plan
```

**Refactor:**
```
refactor: extract audit log query into helper function in jobs route
```

### Rules
- Always **present tense** — "add", not "added" or "adds".
- First line under **50 characters**.
- Reference `docs/` files or edge-case numbers when a commit specifically implements something called out there.
- **One logical change per commit.** Do not mix a bug fix and a new feature in the same commit.

---

## 3. Branching Strategy

### Branch Structure

```
main        ← production-ready, protected, merge via PR only
develop     ← staging/integration branch, always tracks main
  └── feat/phase-2-auth-middleware
  └── feat/phase-2-result-download
  └── fix/celery-retry-policy
  └── ci/fix-build-and-publish-permissions
  └── docs/update-srs-edge-cases
```

### Rules

- **All PRs target `develop`** — never open a PR directly into `main` (except hotfixes).
- **`main` ← `develop` PRs** are opened only when `develop` is stable and all CI passes — this is a "release" merge.
- **Never commit directly to `main` or `develop`** — always work on a feature/fix branch.
- **Always branch from `develop`**, not from a stale local copy:

```bash
git checkout develop
git pull origin develop
git checkout -b feat/phase-2-auth-middleware
```

### Branch Naming Convention

```
<type>/<short-description>
```

| Example | Use case |
|---|---|
| `feat/phase-2-auth-middleware` | New JWT auth feature |
| `feat/phase-2-result-download` | New result download endpoint |
| `feat/phase-3-sse-job-progress` | SSE real-time job updates |
| `fix/audit-log-pagination` | Bug fix for audit log |
| `fix/celery-error-retry` | Celery task retry bug |
| `ci/fix-build-publish-permissions` | CI workflow fix |
| `docs/phase-2-implementation-plan` | Documentation update |
| `chore/update-requirements` | Dependency update |
| `refactor/cleaning-service-extract` | Refactoring |

- Lowercase, hyphens only (no underscores, no spaces).
- Short but specific — anyone reading the branch list should understand what it's for without opening it.
- Include `phase-N` in the name if it's scoped to a specific project phase.

---

## 4. Pull Request Guidelines

### When to Open a PR

When a branch's work is complete and:
1. All tests pass locally (`pytest -q tests/`).
2. Frontend type-check passes (`npm run type-check`).
3. The change does not break the Docker build locally.

### PR Title

Same format as a commit summary:
```
feat: add JWT auth middleware and login endpoint
```

### PR Description Template

```markdown
## What this PR does
[1–3 sentence summary of the change.]

## Why
[Which requirement or docs section this addresses. Example: SRS FR-12, 03_ARCHITECTURE.md Section 4.]

## Changes
- [Bullet list of concrete files changed and what changed in them]
- [Keep it scannable]

## How it was tested
- [What you ran locally or in CI]
- [Any known limitations or edge cases not yet handled]

## Screenshots / output (if relevant)
[Paste terminal output, curl responses, or UI screenshots if useful for the reviewer.]

## Checklist
- [ ] All tests pass (`pytest -q tests/`)
- [ ] TypeScript: zero errors (`npm run type-check`)
- [ ] SOLID checklist from `05_DEVELOPMENT.md` Section 3 verified
- [ ] Edge cases from `02_SRS.md` Section 4 considered (list which)
- [ ] No secrets or credentials in code or logs
- [ ] New endpoints have at least one test in `tests/`
```

### Merge Strategy

- **Squash and merge** if the branch has many small WIP commits — keeps `develop` history readable.
- **Regular merge** if the commit history on the branch is already clean and meaningful.
- Delete the branch after merging — keep the branch list clean.
- The CI must be green before merging — no exceptions.

---

## 5. What's Currently Open (August 2026)

Three copilot-authored PR branches exist on `origin` with CI failures. These need to be resolved or closed before the `develop` branch is set as the default PR target:

| Branch | Issue | Fix Needed |
|---|---|---|
| `copilot/fix-docker-image-build-tests` | Docker compose CI startup failures | Review and merge or close |
| `copilot/fix-sync-job-failure` | HF Spaces sync 429 errors | Already fixed in `main` — can be closed |
| `copilot/fix-test-backend-job` | DQN dep missing in backend CI | Already fixed in `main` — can be closed |

These branches are **not blocking new feature work** — they can be closed without merging since their fixes are already in `main`.

---

## 6. Quick Reference Cheat Sheet

```bash
# Start new work — always from develop
git checkout develop
git pull origin develop
git checkout -b feat/phase-2-auth-middleware

# Commit often — one logical change at a time
git add backend/auth/jwt_handler.py
git commit -m "feat: add JWT encode/decode with expiry handling"

git add backend/auth/dependencies.py
git commit -m "feat: add get_current_user FastAPI dependency"

git add tests/test_auth.py
git commit -m "test: add unit tests for JWT handler and auth dependency"

# Push and open PR into develop
git push origin feat/phase-2-auth-middleware
# → open PR into `develop` on GitHub, use template from Section 4
```

---

## 7. Protected Branch Rules (to configure in GitHub Settings)

| Branch | Rule |
|---|---|
| `main` | Require PR, require CI pass, no direct push, no force push |
| `develop` | Require PR, require CI pass, no direct push |

To configure: GitHub → Settings → Branches → Branch protection rules.

---

## 8. For AI Coding Tools Specifically

- When generating a commit message, always use `<type>: <summary>` from Section 2 — never "update code" or "changes".
- When multiple unrelated changes exist in the working directory, suggest splitting into separate commits rather than one combined commit.
- When a feature is complete, proactively draft the PR title + Markdown description using the Section 4 template, ready to paste into GitHub.
- Always remind to `git pull origin develop` before creating a new branch if it's been more than one session since the last pull.
- Never suggest `git push --force` on `main` or `develop`.
