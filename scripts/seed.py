#!/usr/bin/env python3
"""Database seed script for local development and testing.

Populates:
1. Demo User: demo@example.com (Password: password123)
2. Default Accounts: Primary Checking & Rewards Credit Card
3. Hierarchical Categories: Food & Dining, Housing, Transportation, Income, etc.
4. Baseline confirmed ledger transactions with strict Decimal precision.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.constants import AccountType, TransactionType
from shared.database import get_db_session
from shared.models import Account, Category, Transaction, User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "password123"

# Hierarchy definition: Parent -> [Children]
CATEGORY_TREE = {
    "Income": ["Salary", "Investments", "Freelance"],
    "Food & Dining": ["Groceries", "Restaurants", "Coffee Shops"],
    "Housing": ["Rent/Mortgage", "Utilities", "Internet & Phone"],
    "Transportation": ["Gas/Fuel", "Public Transit", "Auto Maintenance"],
    "Personal Care": ["Healthcare", "Fitness", "Shopping"],
}


async def seed_database() -> None:
    ph = PasswordHasher()
    print("Seeding database with development data...")

    async with get_db_session() as session:
        # 1. Check if demo user already exists
        existing_user = await session.scalar(
            select(User).where(User.email == DEMO_EMAIL)
        )

        if existing_user:
            print(f"User '{DEMO_EMAIL}' already exists (ID: {existing_user.id}). Skipping seed.")
            return

        # 2. Create Demo User
        user = User(
            email=DEMO_EMAIL,
            password_hash=ph.hash(DEMO_PASSWORD),
            is_active=True,
        )
        session.add(user)
        await session.flush()  # Populates user.id
        print(f"✔ Created user: {user.email} (ID: {user.id})")

        # 3. Create Accounts
        checking_acct = Account(
            user_id=user.id,
            name="Primary Checking",
            currency="USD",
            account_type=AccountType.CHECKING,
        )
        credit_card_acct = Account(
            user_id=user.id,
            name="Rewards Credit Card",
            currency="USD",
            account_type=AccountType.CREDIT_CARD,
        )
        session.add_all([checking_acct, credit_card_acct])
        await session.flush()
        print(f"✔ Created accounts: '{checking_acct.name}' and '{credit_card_acct.name}'")

        # 4. Create Category Tree
        category_map: dict[str, Category] = {}
        for parent_name, children in CATEGORY_TREE.items():
            parent_cat = Category(user_id=user.id, name=parent_name, parent_id=None)
            session.add(parent_cat)
            await session.flush()
            category_map[parent_name] = parent_cat

            for child_name in children:
                child_cat = Category(
                    user_id=user.id, name=child_name, parent_id=parent_cat.id
                )
                session.add(child_cat)
                await session.flush()
                category_map[child_name] = child_cat

        print(f"✔ Created {len(category_map)} categories across {len(CATEGORY_TREE)} parent groups")

        # 5. Create Baseline Transactions
        today = date.today()
        transactions = [
            Transaction(
                user_id=user.id,
                account_id=checking_acct.id,
                category_id=category_map["Salary"].id,
                amount=Decimal("3500.00"),
                transaction_type=TransactionType.CREDIT,
                transaction_date=today - timedelta(days=5),
                raw_description="ACH DIRECT DEPOSIT TECH CORP PAYROLL",
                clean_merchant="Tech Corp Payroll",
                is_reviewed=True,
            ),
            Transaction(
                user_id=user.id,
                account_id=checking_acct.id,
                category_id=category_map["Rent/Mortgage"].id,
                amount=Decimal("1450.00"),
                transaction_type=TransactionType.DEBIT,
                transaction_date=today - timedelta(days=4),
                raw_description="AUTO-DEBIT PROPERTY MGMT RENT",
                clean_merchant="Property Management",
                is_reviewed=True,
            ),
            Transaction(
                user_id=user.id,
                account_id=credit_card_acct.id,
                category_id=category_map["Groceries"].id,
                amount=Decimal("128.45"),
                transaction_type=TransactionType.DEBIT,
                transaction_date=today - timedelta(days=2),
                raw_description="WHOLEFDS SOMA 10421 SAN FRANCISCO CA",
                clean_merchant="Whole Foods",
                is_reviewed=True,
            ),
            Transaction(
                user_id=user.id,
                account_id=credit_card_acct.id,
                category_id=category_map["Coffee Shops"].id,
                amount=Decimal("5.75"),
                transaction_type=TransactionType.DEBIT,
                transaction_date=today - timedelta(days=1),
                raw_description="BLUE BOTTLE COFFEE HAYES VALLEY",
                clean_merchant="Blue Bottle Coffee",
                is_reviewed=True,
            ),
            Transaction(
                user_id=user.id,
                account_id=credit_card_acct.id,
                category_id=category_map["Utilities"].id,
                amount=Decimal("84.20"),
                transaction_type=TransactionType.DEBIT,
                transaction_date=today,
                raw_description="PACIFIC GAS & ELECTRIC ONLINE PYMT",
                clean_merchant="PG&E",
                is_reviewed=True,
            ),
        ]
        session.add_all(transactions)
        await session.flush()
        print(f"✔ Created {len(transactions)} verified transactions with exact Decimal amounts")

    print("\nDatabase seeded successfully!")


async def verify_seeded_data() -> None:
    """Read back seeded data to verify ORM relationships and precision."""
    print("\n--- Verifying Seeded Data via SQLAlchemy ORM ---")
    async with get_db_session() as session:
        # Load user with accounts and transactions
        result = await session.execute(
            select(User)
            .where(User.email == DEMO_EMAIL)
            .options(
                selectinload(User.accounts),
                selectinload(User.transactions).selectinload(Transaction.category),
            )
        )
        user = result.scalar_one_or_none()
        assert user is not None, "Demo user not found"

        print(f"User: {user.email}")
        print(f"Accounts ({len(user.accounts)}):")
        for acct in user.accounts:
            print(f"  - [{acct.currency}] {acct.name} ({acct.account_type.value})")

        print(f"\nLedger Transactions ({len(user.transactions)}):")
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for txn in user.transactions:
            cat_name = txn.category.name if txn.category else "Uncategorized"
            sign = "+" if txn.transaction_type == TransactionType.CREDIT else "-"
            print(
                f"  [{txn.transaction_date}] {sign}${txn.amount:>8} | {txn.transaction_type.value:<6} | {cat_name:<16} | {txn.clean_merchant}"
            )
            if txn.transaction_type == TransactionType.CREDIT:
                total_credit += txn.amount
            else:
                total_debit += txn.amount

        net = total_credit - total_debit
        print("-" * 65)
        print(f"Total Inflow:  ${total_credit}")
        print(f"Total Outflow: ${total_debit}")
        print(f"Net Balance:   ${net}")
        assert net == Decimal("1831.60"), f"Expected 1831.60, got {net}"
        print("✔ Precision check passed: Exact net balance verified as $1831.60")


async def main() -> None:
    await seed_database()
    await verify_seeded_data()


if __name__ == "__main__":
    asyncio.run(main())
