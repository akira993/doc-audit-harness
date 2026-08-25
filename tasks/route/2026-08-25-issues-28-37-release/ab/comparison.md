# A/B comparison — workflow (Sonnet subagent) vs codex (Terra medium dispatcher)

- arm-w wall: 330s (12 agents parallel) / arm-c wall: 214s (concurrency 3)

| doc | workflow | codex | agree |
|---|---|---|---|
| AGENTS.md | FAIL | FAIL | = |
| CLAUDE.md | PASS | FAIL | DIFF |
| DESIGN.md | PASS | FAIL | DIFF |
| README.md | FAIL | FAIL | = |
| docs/ops/deployment-runbook.md | WARN | WARN | = |
| docs/requirements/requirements-definition.md | FAIL | FAIL | = |
| docs/requirements/requirements-specification.md | PASS | WARN | DIFF |
| docs/specs/DES-006-frontend-architecture.md | WARN | FAIL | DIFF |
| docs/specs/DES-013-client-detail-page.md | FAIL | FAIL | = |
| docs/specs/DES-019-phase-a-production-infrastructure.md | FAIL | FAIL | = |
| docs/specs/DES-025-document-management.md | WARN | FAIL | DIFF |
| docs/specs/DES-040-case-dashboard.md | WARN | FAIL | DIFF |

agreement: 6/12

## codex rationales (for quality reading)

### AGENTS.md — FAIL
The documented overall coverage requirement of 80% is contradicted by the configured enforced threshold of 92%.

### CLAUDE.md — FAIL
CLAUDE.md incorrectly states that testing.md auto-loads for every Python edit; its configured glob limits it to test files.

### DESIGN.md — FAIL
DESIGN.md states that critical fonts are preloaded as fonts with crossorigin in templates/base_inertia.html, but the sealed template preloads the Google Fonts stylesheet as style instead.

### README.md — FAIL
README は shadcn-vue の基盤を「Radix Vue」と記載するが、現行 UI コンポーネントは Reka UI を直接利用しており、依存関係にも reka-ui が定義されているため矛盾している。

### docs/ops/deployment-runbook.md — WARN
The R1 smoke instructions state that `.env.example` has four `SMOKE_TEST_*` entries, but the sealed source defines and consumes only three, creating a concrete stale operational instruction.

### docs/requirements/requirements-definition.md — FAIL
VisaApplication status is contradicted: the document lists bridging_active as a status, but the current ApplicationStatus choices omit it.

### docs/requirements/requirements-specification.md — WARN
NFR-3 retains an unqualified “initially operate with Django admin” statement although the sealed source routes the operational UI through /app/ and restricts /admin/ to superusers. The later note acknowledges the change, but the normative requirement remains stale/ambiguous.

### docs/specs/DES-006-frontend-architecture.md — FAIL
The document states that the legacy candidate-comparison template remains under Django admin after Inertia migration, but the current source says that view and template were removed and only a compatibility redirect remains.

### docs/specs/DES-013-client-detail-page.md — FAIL
The document says active-case rows use an admin link and an `admin_url` DTO field, but current source uses the Inertia case-detail route via `detail_url`.

### docs/specs/DES-019-phase-a-production-infrastructure.md — FAIL
The document claims HSTS is enabled, but sealed production configuration leaves every HSTS setting disabled by default and fly.toml supplies no overriding environment values.

### docs/specs/DES-025-document-management.md — FAIL
DES-025 incorrectly states that a target-type/ID mismatch violates the exactly-one-target check and yields HTTP 422. The current form sets exactly one FK based on target_type, and the model validates only the count; link validation responses are HTTP 400.

### docs/specs/DES-040-case-dashboard.md — FAIL
The documented capped-queue fallback promises to retain `?scope`, but the current UI hard-codes `/app/cases/` and drops it.
