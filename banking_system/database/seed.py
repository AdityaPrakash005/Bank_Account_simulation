"""Idempotent seed script creating demo Customer, Teller, and Admin users."""

from decimal import Decimal
from database.connection import get_db, init_db
from models.account import Account, AccountStatus, AccountType
from models.transaction import Transaction, TransactionType
from models.user import User, UserRole
from security.crypto import CryptoManager


def seed_data():
    init_db()
    with get_db() as db:
        if db.query(User).first() is not None:
            return  # Database already seeded

        print("Seeding demo accounts into database...")

        # 1. Admin Account
        admin_hash, admin_salt = CryptoManager.hash_pin("9999")
        admin = User(
            username="admin",
            full_name="Chief System Administrator",
            pin_hash=admin_hash,
            pin_salt=admin_salt,
            role=UserRole.ADMIN.value,
        )

        # 2. Customer: Sarah Connor
        sarah_hash, sarah_salt = CryptoManager.hash_pin("1234")
        sarah = User(
            username="sarah",
            full_name="Sarah Connor",
            pin_hash=sarah_hash,
            pin_salt=sarah_salt,
            role=UserRole.CUSTOMER.value,
        )

        # 3. Customer: John Doe
        john_hash, john_salt = CryptoManager.hash_pin("4321")
        john = User(
            username="johndoe",
            full_name="John Doe",
            pin_hash=john_hash,
            pin_salt=john_salt,
            role=UserRole.CUSTOMER.value,
        )

        db.add_all([admin, sarah, john])
        db.flush()

        # Seed Accounts for Sarah
        s_chk = Account(
            account_number="1001001001",
            user_id=sarah.id,
            account_type=AccountType.CHECKING.value,
            balance=Decimal("4250.75"),
            status=AccountStatus.ACTIVE.value,
        )
        s_sav = Account(
            account_number="1001001002",
            user_id=sarah.id,
            account_type=AccountType.SAVINGS.value,
            balance=Decimal("18900.00"),
            status=AccountStatus.ACTIVE.value,
        )

        # Seed Account for John
        j_chk = Account(
            account_number="2002002001",
            user_id=john.id,
            account_type=AccountType.CHECKING.value,
            balance=Decimal("1500.00"),
            status=AccountStatus.ACTIVE.value,
        )
        db.add_all([s_chk, s_sav, j_chk])
        db.flush()

        # Sample Initial Transactions
        t1 = Transaction(
            account_id=s_chk.id,
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("5000.00"),
            balance_after=Decimal("5000.00"),
            description="Payroll Direct Deposit",
        )
        t2 = Transaction(
            account_id=s_chk.id,
            type=TransactionType.WITHDRAWAL.value,
            amount=Decimal("749.25"),
            balance_after=Decimal("4250.75"),
            description="Lease payment debit",
        )
        t3 = Transaction(
            account_id=s_sav.id,
            type=TransactionType.DEPOSIT.value,
            amount=Decimal("18900.00"),
            balance_after=Decimal("18900.00"),
            description="Wire transfer inbound",
        )
        db.add_all([t1, t2, t3])
        print("Database seeded successfully with default accounts.")


if __name__ == "__main__":
    seed_data()