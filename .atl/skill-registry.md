# Skill Registry — sistema-pos

**Generated**: 2026-05-06
**Project**: sistema-pos (Django 5.2 POS system)
**Scope**: SDD orchestration + Python/Django development

---

## Available Skills

### SDD Framework Skills (User-Level)
Core Spec-Driven Development workflow orchestration and execution.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **sdd-init** | `/sdd-init` or init system prompt marker | Initialize SDD context, detect stack, bootstrap persistence backend |
| **sdd-explore** | `/sdd-explore <topic>` | Investigate ideas, explore codebase, clarify requirements |
| **sdd-propose** | Internal phase after explore | Create change proposal with intent, scope, approach |
| **sdd-spec** | `/sdd-spec [change]` | Write specifications with requirements and scenarios |
| **sdd-design** | `/sdd-design [change]` | Create technical design with architecture decisions |
| **sdd-tasks** | `/sdd-tasks [change]` | Break down spec/design into implementation tasks |
| **sdd-apply** | `/sdd-apply [change]` | Implement tasks, write actual code following specs/design |
| **sdd-verify** | `/sdd-verify [change]` | Validate implementation matches specs, design, tasks |
| **sdd-archive** | `/sdd-archive [change]` | Sync delta specs and archive completed change |
| **sdd-onboard** | `/sdd-onboard` | Guided end-to-end SDD cycle walkthrough |

### Review & Delivery Skills (User-Level)
PR and code review workflows.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **branch-pr** | When creating PR, preparing changes for review | PR creation workflow following issue-first enforcement |
| **chained-pr** | When PR would exceed 400 changed lines | Split large changes into stacked/chained PRs for review |
| **work-unit-commits** | When implementing change, preparing commits | Structure commits as deliverable units, not file-type batches |

### Documentation & Collaboration Skills (User-Level)
Writing and review practices for team collaboration.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **cognitive-doc-design** | When writing guides, READMEs, docs | Design docs that reduce cognitive load through chunking |
| **comment-writer** | When drafting PR/issue/review comments | Write warm, direct, human feedback for async collaboration |

### Specialized Skills (User-Level)
Language and framework-specific testing patterns.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **go-testing** | When writing Go tests, using teatest | Go testing patterns (not applicable to this project) |

### Meta Skills (User-Level)
Skill management and project conventions.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **skill-registry** | `update skills` or after installing/removing | Create/update skill registry for current project |
| **skill-creator** | When creating new AI agent skills | Create new skills following Agent Skills spec |
| **judgment-day** | `judgment day`, `doble review`, `juzgar` | Parallel adversarial review (2 blind judges) |

### Shared Resources (Internal)
- **_shared**: Common references for SDD phases (engram convention, openspec convention, skill resolver)

---

## Project Conventions

### AGENTS.md — Project Reference
**Path**: `AGENTS.md` (project root)  
**Content**: 
- Project summary (Django 5.2 POS for Peruvian retail)
- Essential setup commands (venv, migrate, Docker)
- Architecture overview (usuarios model complete; others scaffold)
- Git workflow (main ← develop ← feature/*)
- Gotchas (PostgreSQL required, .env mandatory, JWT-only auth, custom User model)
- Team context (5 students, USS Chiclayo, SUNAT integration required)

**Usage**: Referenced by all phases; critical for understanding project scope and constraints.

---

## Compact Rules for Sub-Agents

### Django/DRF Code Context
**Applies to**: sdd-apply, sdd-verify when writing/reviewing Python code

```markdown
## Project Standards (Django/DRF — sistema-pos)

**Custom User Model**: Always use `from django.contrib.auth import get_user_model; User = get_user_model()` 
  or `settings.AUTH_USER_MODEL` in queries. Never hardcode `django.contrib.auth.models.User`.

**Test Structure**: Use Django TestCase in `tests.py` of each app. No pytest/coverage yet.
  Command: `python manage.py test`

**API Response Format**: Use DRF APIView or ViewSet with drf-spectacular decorators for OpenAPI.
  All endpoints must have `@extend_schema()` for documentation.

**Locale**: es-pe (Spanish, Peru). Time zone: America/Lima. Currency: PEN (S/).

**Auth**: JWT Bearer tokens only (DRF SimpleJWT). No session auth.
  Token format: `Authorization: Bearer <token>`

**Database**: PostgreSQL 15 required. No SQLite fallback. Test database must be Postgres.
  Connection: via python-decouple from .env (SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).
```

### Documentation Style
**Applies to**: cognitive-doc-design when writing guides, READMEs, architecture docs

```markdown
## Project Standards (Documentation — sistema-pos)

**Language**: Spanish (es-pe) with English code examples.

**Audience**: 5-person university team; assume basic Django knowledge, not deep DRF/auth.

**Structure**: Progressive disclosure — quick start first, then architecture, then details.
  Use checklists, tables, and signposting.

**SUNAT Integration Note**: Always mention when feature affects electronic invoicing flow (UBL 2.1, PSE/OSE).
```

### PR & Review Practices
**Applies to**: branch-pr, chained-pr, comment-writer when creating/reviewing PRs

```markdown
## Project Standards (PRs — sistema-pos)

**Target Branch**: PRs to `develop`, merge to `main` only when stable.

**Size Limit**: Max 400 changed lines per PR (for cognitive review budget).
  Exceeded? Use chained-pr to split into stacked slices.

**Commit Style**: Conventional commits (feat:, fix:, docs:, test:, refactor:).
  No "Co-Authored-By" or AI attribution.

**Test Coverage**: Every PR that adds features must include tests (django.test.TestCase).
  Coverage requirement: new code ≥ 80% covered.

**Review Checklist**:
  - [ ] Custom User model usage correct?
  - [ ] No hardcoded auth.User?
  - [ ] @extend_schema present on all new API endpoints?
  - [ ] Tests pass locally (python manage.py test)?
  - [ ] .env.example updated if new config added?
```

---

## Trigger Matching Rules

### When to Load Which Skill

| Context | Matched Skills |
|---------|---|
| **User invokes `/sdd-init`** | sdd-init |
| **User invokes `/sdd-explore <topic>`** | sdd-explore |
| **User invokes `/sdd-new <change>` or `/sdd-ff`** | sdd-propose (after explore) |
| **Writing specs or scenarios** | sdd-spec, cognitive-doc-design |
| **Writing architecture design** | sdd-design, cognitive-doc-design |
| **Breaking down tasks** | sdd-tasks, work-unit-commits |
| **Implementing Python/Django code** | sdd-apply, work-unit-commits |
| **Running tests or verification** | sdd-verify |
| **Creating PR or reviewing code** | branch-pr, chained-pr (if >400 lines), comment-writer |
| **Archiving completed change** | sdd-archive |
| **Adversarial review requested** | judgment-day |

---

## Engram Topic Keys (SDD Persistence)

When using engram as artifact store, use these topic keys:

| Artifact | Topic Key |
|----------|-----------|
| Project context | `sdd-init/sistema-pos` |
| Testing capabilities | `sdd/sistema-pos/testing-capabilities` |
| Change exploration | `sdd/{change-name}/explore` |
| Change proposal | `sdd/{change-name}/proposal` |
| Change specification | `sdd/{change-name}/spec` |
| Change design | `sdd/{change-name}/design` |
| Change tasks | `sdd/{change-name}/tasks` |
| Apply progress | `sdd/{change-name}/apply-progress` |
| Verify report | `sdd/{change-name}/verify-report` |
| Archive report | `sdd/{change-name}/archive-report` |

---

## Next Steps

1. **First SDD Change**: Use `/sdd-new <change-name>` to start your first change
2. **Choose Artifact Store**: engram (fast, local) vs openspec (file-based, shareable) vs hybrid (both)
3. **Choose Execution Mode**: auto (silent, back-to-back) vs interactive (ask after each phase)
4. **Enable Tests**: Install pytest-django and pytest-cov to expand testing capabilities
5. **Add Linting**: Install ruff (linter) and pyright (type checker) for code quality

---

**Registry maintained by**: sdd-init + skill-registry  
**Last updated**: 2026-05-06  
**Project**: sistema-pos
