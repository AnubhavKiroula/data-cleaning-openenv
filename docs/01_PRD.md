# Product Requirements Document (PRD) — data-cleaning-openenv

> **For AI coding tools:** This document defines *what* we're building and *why*. Before implementing any new feature, verify it serves one of the goals in Section 5. If a proposed change is in Section 6 (Non-Goals), do not implement it without explicit team approval.

---

## 1. Project Name

**data-cleaning-openenv** — An autonomous, RL-powered data cleaning platform.

---

## 2. Problem Statement

Data preparation consumes **60–80% of a data scientist's time** (industry benchmark). The current state:
- **Manual cleaning**: slow, inconsistent, non-reproducible, does not scale beyond small datasets.
- **Rule-based scripts**: brittle — they break on new data patterns and need constant maintenance.
- **No learned feedback**: existing tools do not improve their cleaning decisions based on outcomes.

There is no system that:
1. Autonomously detects *which type* of quality issue affects a given cell/row.
2. Selects the *optimal cleaning action* from multiple possible strategies based on learned experience.
3. Logs a full, auditable trace of every decision made, with which agent made it and why.

---

## 3. What We're Building

A **multi-agent RL-powered data cleaning platform** that:
- Accepts raw CSV/Excel datasets via a REST API.
- Runs a DQN-based ensemble of specialist agents that each own a distinct cleaning domain (missing data, duplicates, outliers, type inference, normalization).
- An **AgentCoordinator** selects the best agent per observation and logs each action with its reward.
- Results and full audit trails are persisted in PostgreSQL and downloadable as cleaned CSVs.
- A React SPA provides an end-to-end user experience: upload → monitor → inspect audit log → export.

---

## 4. Who This Is For

| User | Need |
|---|---|
| **Data Scientists / ML Engineers** | Clean datasets before training, with a full audit trail showing what was changed and why |
| **Data Analysts** | Upload messy CSVs from business operations and get cleaned versions without writing code |
| **Developers / API Consumers** | Use the REST API to integrate automated cleaning into existing pipelines |
| **Project Evaluators / Reviewers** | Assess the RL architecture, code quality, and production-readiness of the platform |

---

## 5. Goals

1. **Correct RL decision-making:** The DQN-based coordinator reliably selects the highest-value cleaning action for each observation.
2. **Full audit transparency:** Every action is logged — which agent acted, what was changed, what the reward was.
3. **Async scalability:** Large datasets (tens of thousands of rows) are processed asynchronously via Celery without blocking the API.
4. **Production-grade code quality:** SOLID principles, type hints, Google-style docstrings, no hardcoded values — all enforced.
5. **Usable immediately:** A new developer should be able to clone, run `docker compose up`, and have a working system in under 5 minutes.
6. **Observable:** Prometheus metrics, structured logs, and `/api/health` endpoint for monitoring.

---

## 6. Non-Goals (explicitly out of scope)

- **Real-time collaborative editing** of datasets by multiple users simultaneously.
- **Deep learning / NLP-based cleaning** (e.g., entity resolution, semantic deduplication) — out of scope for v1.
- **Multi-tenant SaaS** — auth is scoped to a single-tenant deployment for now.
- **Mobile app** — web-first only.
- **Manual cleaning step UI** — the system is autonomous; a "human review" step is a future stretch goal.

> [!IMPORTANT]
> Any AI-generated code that introduces a feature in this Non-Goals list must be flagged and removed before merging.

---

## 7. Success Criteria

- **96/96 tests pass** on every commit to `main` and `develop`.
- **TypeScript strict mode** with zero errors on frontend build.
- **End-to-end flow** works: upload CSV → start job → poll to completion → download cleaned CSV.
- **Audit log** shows correct agent, action, old/new value, and reward for every processed row.
- **CI pipeline** passes for all 3 stages: unit tests, Docker build, smoke test.
- **Metrics endpoint** responds with Prometheus-formatted counters at `GET /metrics`.

---

## 8. Phase Completion Targets

| Phase | Target Status | Key Deliverable |
|---|---|---|
| Phase 1: RL Engine | ✅ Done | 5 agents, DQN, 96 tests |
| Phase 2: Backend | 85% → **100%** | Auth middleware, rate limiting, result download, pagination |
| Phase 3: Frontend | 80% → **100%** | SSE real-time updates, auth login page |
| Phase 4: DevOps | 65% → **100%** | Fixed CI, staging env, prod deployment |

---

## 9. Reference Diagrams

For system architecture, data flow, module map, and ER diagram, see:
**[`00_PROJECT-OVERVIEW-AND-DIAGRAMS.md`](./00_PROJECT-OVERVIEW-AND-DIAGRAMS.md)**

---

**Any team member or AI tool proposing a new feature must check it against Sections 5 and 6 before implementing it.**
