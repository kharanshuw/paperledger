"""Central API v1 router consolidating domain sub-routers."""

from fastapi import APIRouter
from app.api.v1 import accounts, auth, categories, transactions

api_router = APIRouter()

# Mount domain routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
# api_router.include_router(statements.router, prefix="/statements", tags=["Statements"])
