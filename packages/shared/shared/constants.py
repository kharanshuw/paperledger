"""Shared domain constants, enums, and invariant definitions."""

from enum import Enum


class TransactionType(str, Enum):
    """Direction of funds for double-entry bookkeeping discipline."""

    DEBIT = "DEBIT"  # Outflow / Expense
    CREDIT = "CREDIT"  # Inflow / Income


class StatementStatus(str, Enum):
    """Lifecycle status of a batch uploaded bank statement."""

    QUEUED = "QUEUED"  # Uploaded, waiting for worker consumption
    PROCESSING = "PROCESSING"  # Actively being parsed by Celery worker
    COMPLETED = "COMPLETED"  # Parsed and staged in staged_transactions
    FAILED = "FAILED"  # Error occurred during extraction or layout parsing


class StagedStatus(str, Enum):
    """Status of a staged transaction awaiting user review before ledger commit."""

    PENDING_REVIEW = "PENDING_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class AccountType(str, Enum):
    """Types of financial accounts supported by the platform."""

    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    INVESTMENT = "INVESTMENT"
    CASH = "CASH"
