"""Transaction API endpoints for confirmed double-entry ledger records."""

from datetime import date
import uuid
from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.transaction import (
    PaginatedTransactionsResponse,
    TransactionCreateRequest,
    TransactionResponse,
    TransactionUpdateRequest,
)
from app.services.transaction_service import TransactionService
from shared.constants import TransactionType

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedTransactionsResponse,
    summary="List transactions with filters",
    description="Returns paginated transactions with optional account, category, type, and date range filters.",
)
async def list_transactions(
    current_user: CurrentUserDep,
    db: SessionDep,
    account_id: uuid.UUID | None = Query(default=None, description="Filter by account UUID"),
    category_id: uuid.UUID | None = Query(default=None, description="Filter by category UUID"),
    transaction_type: TransactionType | None = Query(default=None, description="Filter by direction: DEBIT or CREDIT"),
    start_date: date | None = Query(default=None, description="Filter transactions on or after this date"),
    end_date: date | None = Query(default=None, description="Filter transactions on or before this date"),
    limit: int = Query(default=50, ge=1, le=200, description="Page limit (max 200)"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
) -> PaginatedTransactionsResponse:
    """List filtered ledger transactions."""
    return await TransactionService.list_transactions(
        session=db,
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionResponse,
    summary="Record manual transaction",
    description="Atomically records a verified transaction in the primary double-entry ledger.",
)
async def create_transaction(
    req: TransactionCreateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> TransactionResponse:
    """Create manual transaction."""
    return await TransactionService.create_transaction(db, current_user.id, req)


@router.get(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="Retrieves a specific transaction record by UUID, verifying tenant ownership.",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> TransactionResponse:
    """Get single transaction."""
    return await TransactionService.get_transaction(db, current_user.id, transaction_id)


@router.patch(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=TransactionResponse,
    summary="Update transaction",
    description="Updates transaction categorization, narration, or amount.",
)
async def update_transaction(
    transaction_id: uuid.UUID,
    req: TransactionUpdateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> TransactionResponse:
    """Update transaction."""
    return await TransactionService.update_transaction(db, current_user.id, transaction_id, req)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete transaction",
    description="Permanently deletes a transaction from the ledger.",
)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> Response:
    """Delete transaction."""
    await TransactionService.delete_transaction(db, current_user.id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
