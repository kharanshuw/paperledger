"""Account API endpoints for managing user financial accounts."""

import uuid
from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUserDep, SessionDep
from app.schemas.account import AccountCreateRequest, AccountResponse, AccountUpdateRequest
from app.services.account_service import AccountService

router = APIRouter()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[AccountResponse],
    summary="List all user accounts",
    description="Returns all financial accounts owned by the authenticated tenant.",
)
async def list_accounts(
    current_user: CurrentUserDep,
    db: SessionDep,
) -> list[AccountResponse]:
    """List tenant accounts."""
    return await AccountService.list_accounts(db, current_user.id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AccountResponse,
    summary="Create financial account",
    description="Creates a new financial account (e.g. Checking, Savings, Credit Card) for the current user.",
)
async def create_account(
    req: AccountCreateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> AccountResponse:
    """Create a new account."""
    return await AccountService.create_account(db, current_user.id, req)


@router.get(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=AccountResponse,
    summary="Get account by ID",
    description="Fetches a specific account by its UUID, verifying tenant ownership.",
)
async def get_account(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> AccountResponse:
    """Retrieve single account."""
    return await AccountService.get_account(db, current_user.id, account_id)


@router.patch(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    response_model=AccountResponse,
    summary="Update account",
    description="Updates account name, currency, or categorization.",
)
async def update_account(
    account_id: uuid.UUID,
    req: AccountUpdateRequest,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> AccountResponse:
    """Update existing account."""
    return await AccountService.update_account(db, current_user.id, account_id, req)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete account",
    description="Deletes an account owned by the current user. Cascades to associated transactions.",
)
async def delete_account(
    account_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: SessionDep,
) -> Response:
    """Delete an account."""
    await AccountService.delete_account(db, current_user.id, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
