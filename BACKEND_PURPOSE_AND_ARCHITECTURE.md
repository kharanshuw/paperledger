# Backend System Purpose & Architectural Charter (`BACKEND_PURPOSE_AND_ARCHITECTURE.md`)

## 1. System Vision & Problem Statement

Personal expense tracking fails primarily due to manual data-entry fatigue. Users track expenses consistently for a few days, skip entries, and abandon the tool.

The primary purpose of this backend platform is to **eliminate entry friction while maintaining audit-grade financial accuracy**. It accomplishes this by supporting two distinct ingestion paths:

1. **Ad-hoc real-time entry:** Fast, lightweight recording of single transactions via mobile or web client.
2. **Automated statement ingestion:** Batch processing of monthly PDF bank or credit card statements that extracts tabular transaction histories, detects duplicates, normalizes merchant descriptors, and stages records for user verification.

---

## 2. Core Functional Responsibilities

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                    FastAPI Core Service                  │
                               │                                                          │
Manual Entry ─────────────────►│ 1. Validate Category & Account Schema                    │
                               │ 2. Insert Transaction Atomically (ACID)                  │
                               │ 3. Invalidate/Update User Rolling Analytics Cache        │
                               └──────────────────────────┬───────────────────────────────┘
                                                          │
                                                          ▼
                                              PostgreSQL (Primary Ledger)
                                                          ▲
                                                          │
PDF Statement ────────────────►┌──────────────────────────┴───────────────────────────────┐
Upload                         │               Statement Ingestion Domain                 │
                               │ 1. Compute SHA-256 Checksum (De-duplication)             │
                               │ 2. Stream Binary to Disk/Object Store                    │
                               │ 3. Enqueue Job -> Redis (Broker)                         │
                               └──────────────────────────┬───────────────────────────────┘
                                                          │
                                                          ▼
                               ┌──────────────────────────────────────────────────────────┐
                               │              Celery Parser Worker Service                │
                               │                                                          │
                               │ 1. Coordinate-based extraction (pdfplumber)              │
                               │ 2. Clean & normalize merchants + ISO 8601 UTC dates      │
                               │ 3. Run Duplicate Reconciliation against Primary Ledger   │
                               │ 4. Commit to `staged_transactions` with confidence score │
                               └──────────────────────────────────────────────────────────┘
```

The backend is composed of two containerized Python applications working in tandem:

### A. Core API (`services/core-api`)

* **Identity & Tenancy:** Multi-tenant user isolation. Every query must strictly scope data by `user_id`.
* **Primary Ledger:** Absolute source of truth for confirmed accounts, categories, and debits/credits.
* **Upload Gateway:** Accepts PDF uploads via streaming chunks, validates PDF magic bytes, calculates SHA-256 hashes to reject duplicate files, saves the binary, and produces a job payload for Redis.
* **Reporting & Analytics:** Serves aggregates (monthly spend, spend-by-category, period-over-period delta) without full-table scans.

### B. Statement Parser Worker (`services/parser-worker`)

* **Asynchronous Execution:** Runs isolated from HTTP request lifecycles.
* **Layout-Aware Extraction:** Extracts tabular lines using bounding-box heuristics rather than naive text dumps.
* **Sanitization Engine:** Converts heterogeneous statement strings (e.g., `POS DEBIT 4821 *STARBUCKS SEATTLE WA` $\rightarrow$ `Starbucks`).
* **Staged Reconciliation:** Writes extracted records to a staging table so the user can verify them before they merge into the active ledger.

---

## 3. Financial & Business Invariants (Non-Negotiable)

1. **Absolute Numerical Precision:**
   - **Rule:** Never cast money values to standard binary floats (`float` or `double`).
   - **Implementation:** Always use Python `decimal.Decimal` and PostgreSQL `NUMERIC(12, 2)`. Amounts must be parsed strictly from string tokens.

2. **Double-Entry Discipline:**
   - Every transaction must specify a transaction direction: `DEBIT` (outflow/expense) or `CREDIT` (inflow/income).

3. **De-duplication & Reconciliation Heuristics:**
   - A user may log an expense manually and later upload a statement containing that same expense. The worker must calculate a deduplication match probability:

$$\text{Match Candidate} = (\text{Same Account}) \land (\text{Same Amount}) \land (\vert{}Date_{\text{manual}} - Date_{\text{statement}}\vert{} \le 3\text{ days}) \land (\text{Levenshtein}(Desc_1, Desc_2) \ge 0.75)$$

   - High-confidence matches must be flagged as `is_potential_duplicate = true` with a pointer to the existing transaction ID rather than silently writing a duplicate entry.

4. **Statement Staging Pattern:**
   - Statement lines must never write directly into the live `transactions` table. They must land in `staged_transactions` with status `PENDING_REVIEW` until the user confirms or adjusts categories.

---

## 4. Hardware Constraints & Resource Discipline

The backend will run on a single Google Compute Engine VM provisioned with **2 vCPUs and 4 GB RAM** under K3s.

To maintain system stability without triggering Linux kernel Out-Of-Memory (`OOMKilled`) termination:

* **Core API Pod:** Capped at **300 MiB RAM**. Run with Uvicorn utilizing an async event loop (`uvloop`).
* **Worker Pod:** Capped at **800 MiB RAM**. Set Celery flags:
```bash
celery -A tasks.celery_app worker --concurrency=1 --max-tasks-per-child=20 --loglevel=info
```
*(Concurrency is intentionally locked to `1` so the single node only extracts one PDF at any given moment).*

* **Streaming Uploads:** Do not read full file buffers into memory:
```python
# CORRECT: Memory-efficient streaming
with open(destination_path, "wb") as buffer:
    while chunk := await file.read(1024 * 1024): # 1MB chunks
        buffer.write(chunk)
```

---

## 5. Domain Entities & Database Schema

The backend agent must implement and maintain the following core schema:

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│     users       │       │    accounts     │       │    categories    │
├─────────────────┤       ├─────────────────┤       ├──────────────────┤
│ id (UUID, PK)   │◄──┐   │ id (UUID, PK)   │◄──┐   │ id (UUID, PK)    │
│ email (VARCHAR) │   └───┤ user_id (FK)    │   └───┤ user_id (FK)     │
│ password_hash   │       │ name (VARCHAR)  │       │ name (VARCHAR)   │
│ created_at      │       │ currency (CHAR3)│       │ parent_id (FK)   │
└─────────────────┘       └────────┬────────┘       └────────┬─────────┘
                                   │                         │
                                   │                         │
                                   ▼                         ▼
┌─────────────────┐       ┌────────────────────────────────────────────┐
│   statements    │       │                transactions                │
├─────────────────┤       ├────────────────────────────────────────────┤
│ id (UUID, PK)   │       │ id (UUID, PK)                              │
│ user_id (FK)    │       │ user_id (FK)                               │
│ account_id (FK) │       │ account_id (FK)                            │
│ file_hash       │       │ category_id (FK, nullable)                 │
│ storage_path    │       │ statement_id (FK, nullable)                │
│ status (ENUM)   │       │ amount (NUMERIC(12,2))                     │
└────────┬────────┘       │ transaction_type (DEBIT/CREDIT)            │
         │                │ transaction_date (DATE)                    │
         ▼                │ raw_description (TEXT)                     │
┌─────────────────────────┴─────────┐ clean_merchant (VARCHAR)         │
│        staged_transactions        │ is_reviewed (BOOLEAN)              │
├───────────────────────────────────┤ created_at (TIMESTAMPTZ)           │
│ id (UUID, PK)                     └────────────────────────────────────┘
│ statement_id (FK)                 
│ suggested_category_id (FK)        
│ amount (NUMERIC(12,2))            
│ transaction_date (DATE)           
│ raw_description (TEXT)            
│ potential_duplicate_id (FK)       
│ status (PENDING/CONFIRMED/REJECTED)
└───────────────────────────────────┘
```

---

## 6. Communication Protocols & Contracts

1. **Synchronous Ingestion:** RESTful JSON over HTTP for manual operations, authentication, and CRUD endpoints (`/api/v1/transactions`, `/api/v1/categories`, `/api/v1/accounts`).
2. **Asynchronous Ingestion:** HTTP POST `/api/v1/statements/upload` returns an immediate `202 Accepted` response with `{ "job_id": "<uuid>", "status": "QUEUED" }`.
3. **Status Polling / Real-time Push:** Implement an endpoint at `/api/v1/statements/{statement_id}/status` allowing the client to poll parse progress (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`).
4. **Error Modeling:** Strictly emit RFC 7807 compliant JSON problem details for domain failures (`DUPLICATE_STATEMENT`, `INVALID_FILE_SIGNATURE`, `CORRUPTED_PDF`).
