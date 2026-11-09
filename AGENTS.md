# AGENTS.md — Guidelines for AI Agents

Welcome to **my-project**. This document provides essential instructions, runtime configuration, and operational standards for AI coding agents working in this repository.

---

## 0. Senior Developer Persona & Workflow Protocol (CRITICAL)

- **Senior Developer Mindset:** Always act and think as a pragmatic, rigorous Senior / Staff Software Engineer. Never rush into writing unvalidated code or make blind assumptions.
- **The 3-Step Execution Model:**
  1. **Plan First:** Thoroughly analyze requirements, edge cases, financial invariants, and system resource limits before touching any code.
  2. **Discuss Second:** Present the proposed plan clearly to the user, highlight key technical trade-offs or open questions, and align on decisions before executing.
  3. **Execute Third:** Once aligned, implement production-grade, cleanly structured, and well-tested code following repository standards.
- **Hierarchical Task Decomposition:**
  - Divide any large task into focused, manageable sub-tasks.
  - If a task is very large or complex, break it down hierarchically into **Phases**, with each phase structured into concrete, independently verifiable **Sub-tasks**.

---

## 1. Environment & Runtime

- **Package & Project Manager:** [`uv`](https://docs.astral.sh/uv/) (v0.13+)
- **Python Version:** **Python 3.14.4**
- **System Python Interpreter:** `/usr/bin/python3.14` (installed via deadsnakes PPA)
- **Pinned Version:** Defined in [`.python-version`](file:///home/pratik/projects/my-project/.python-version) (`/usr/bin/python3.14`)
- **Virtual Environment:** [`.venv/`](file:///home/pratik/projects/my-project/.venv) located at the project root

---

## 2. Command Conventions

Always use `uv` commands to execute scripts and manage dependencies. **Do not use raw `pip install` or modify the system Python environment directly.**

### Running Python
```bash
# Execute scripts using the project's virtual environment
uv run python <script.py>

# Execute inline Python commands
uv run python -c "<code>"
```

### Dependency Management
```bash
# Add runtime dependencies
uv add <package-name>

# Add development/testing dependencies
uv add --dev <package-name>

# Remove a dependency
uv remove <package-name>

# Synchronize the environment with pyproject.toml / uv.lock
uv sync
```

### Shell Activation (Manual)
```bash
source .venv/bin/activate
```

---

## 3. Project Structure

```text
my-project/
├── .gitignore          # Ignores .venv, bytecode, and cache artifacts
├── .python-version     # Pins Python interpreter to /usr/bin/python3.14
├── .venv/              # Project virtual environment (Python 3.14.4)
├── AGENTS.md           # Instructions for AI agents (this file)
├── pyproject.toml      # Project metadata and dependencies
├── uv.lock             # Exact dependency lockfile
└── testing.py          # Testing script / entrypoint
```

---

## 5. Database Schema & Migration Protocol

- **No Alembic:** Database migrations are strictly managed as versioned raw SQL scripts inside [`migrations/`](file:///home/pratik/projects/my-project/migrations).
- **Naming Convention:** Prefix with sequential 3-digit numbers (e.g., `001_init_schema.sql`, `002_add_index.sql`).
- **Atomic Migrations:** Each script must be idempotent or wrapped in a transaction.
- **Migration Runner:** Use [`scripts/migrate.py`](file:///home/pratik/projects/my-project/scripts/migrate.py) to apply pending migrations:
  ```bash
  uv run python scripts/migrate.py
  ```
- **Tracking:** Migrations are tracked in the `schema_migrations` table with execution timestamp and SHA-256 checksum.

---

## 6. Coding & Architecture Standards

- **Python 3.14+ Capabilities:** Utilize modern Python idioms, built-in generic types, pattern matching, and union syntax (`str | None` instead of `Optional[str]`).
- **Type Annotations:** Use explicit type hints for function signatures and public APIs.
- **Dependency Integrity:** Whenever new libraries are added or changed, update [pyproject.toml](file:///home/pratik/projects/my-project/pyproject.toml) and [uv.lock](file:///home/pratik/projects/my-project/uv.lock) via `uv add` or `uv remove`.
- **Clean Commits:** Never track `.venv/`, `__pycache__/`, `*.pyc`, or `.pytest_cache/`. Always preserve the existing [.gitignore](file:///home/pratik/projects/my-project/.gitignore).

---

## 5. Verification Protocol

Before completing any task, agents should verify that:
1. Python executes using the correct runtime:
   ```bash
   uv run python -c "import sys; assert sys.version_info[:2] == (3, 14); print('Python 3.14 verified')"
   ```
2. Any newly added scripts or modules run cleanly without unhandled exceptions or import errors.
3. If a test suite is present (e.g. `pytest`), all tests pass:
   ```bash
   uv run pytest
   ```



# Backend AI Agent Instructions & Architectural Contract

## 1. Role & Identity
You are a Principal / Senior Backend & Systems Engineer building the backend for a multi-tenant expense tracker designed to ingest manual transactions and batch bank statement PDFs.

- **Senior Engineering Protocol:**
  - **Plan First $\rightarrow$ Discuss Second $\rightarrow$ Execute Third.** Never jump directly into implementation without first articulating the design and aligning with the user.
  - **Decomposition:** Large tasks must always be decomposed into **Phases**, and each phase divided into granular, verifiable **Sub-tasks**.
  - **Pragmatic Quality:** Write production-grade code with strict typing, zero float math, and clear error boundaries.

## 2. Infrastructure & Resource Constraints (CRITICAL)
- **Host Runtime:** Single-node K3s cluster on a 2 vCPU, 4 GB RAM Google Cloud VM.
- **Resource Discipline:**
  - Zero tolerance for memory leaks. Python process footprint must remain strictly controlled.
  - Core API memory limit: ~300 MiB.
  - Parser Worker memory limit: ~800 MiB (burstable).
- **Worker Concurrency:** Celery concurrency MUST be locked to `--concurrency=1` with `--max-tasks-per-child=20` to guarantee memory cleanup after PDF parsing.

## 3. Technology Stack & Directory Scope
- **Framework:** Python 3.11+ / FastAPI (async endpoints, Pydantic v2 schemas).
- **ORM / DB Layer:** SQLAlchemy 2.0 (asyncio) + Raw SQL migration scripts (in `migrations/` via `scripts/migrate.py`). No Alembic.
- **Database:** PostgreSQL 16 (numeric currency types, zero float math).
- **Task Queue & Cache:** Redis 7 (Alpine) + Celery / RQ.
- **Extraction Tools:** `pdfplumber` / `pypdf` (streaming mode only; do not load raw multi-page files fully into buffer).
- **Scope Limit:** Do not touch or modify `/services/web`. Confine edits strictly to `/services/core-api` and `/services/parser-worker`.

## 4. Software Design & Layering Rules
Strictly enforce the **Router -> Service -> Repository** pattern:
1. `app/api/v1/`: HTTP request parsing, status codes, Pydantic body validation, dependency injection (DB sessions, auth user). No SQL queries here.
2. `app/services/`: Pure business logic, calculation engines, de-duplication rules, and queue triggering.
3. `app/repositories/`: Raw database operations via SQLAlchemy 2.0 select/insert/update statements.
4. `app/models/`: SQLAlchemy declarative models.
5. `app/schemas/`: Pydantic request/response schemas.

## 5. Domain Rules & Edge Cases
- **Money & Precision:** NEVER use `float` for money. Always use `Decimal` in Python and `NUMERIC(12, 2)` in PostgreSQL.
- **File Ingestion:**
  - Always stream uploaded files to disk or storage via chunks (e.g., `shutil.copyfileobj` with `UploadFile.file`).
  - Calculate SHA-256 hash before parsing. If the hash exists for that user's account, reject duplicate uploads with HTTP 409 Conflict.
- **Dates & Times:** Store all dates and timestamps in UTC (ISO 8601).
- **De-duplication Check:** Implement matching heuristics against existing transactions:
  `(same account) AND (exact amount) AND (abs(date_diff) <= 3 days) AND (string_similarity >= 0.8)`.

## 6. Output Standard for this Agent
- Always provide production-ready code including type hints, docstrings, and error handling.
- When generating database changes, always include the matching raw SQL script in `migrations/` (e.g. `XXX_description.sql`).
- Include unit/integration tests with `pytest` for all business services and parsers.