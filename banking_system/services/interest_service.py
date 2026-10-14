"""Automated and on-demand interest accrual engine."""

from decimal import Decimal
from typing import Tuple
from database.connection import get_db
from models.account import Account, AccountStatus, AccountType
from models.transaction import Transaction, TransactionType
from services.audit_service import AuditService


class InterestService:
    DEFAULT_RATES = {
        AccountType.SAVINGS.value: Decimal("0.035"),  # 3.5%
        AccountType.CHECKING.value: Decimal("0.005"),  # 0.5%
        AccountType.MONEY_MARKET.value: Decimal("0.050"),  # 5.0%
    }

    @classmethod
    def apply_account_interest(cls, account_id: str, actor: str) -> Tuple[bool, str]:
        with get_db() as db:
            acc = db.query(Account).filter(Account.id == account_id).with_for_update().first()
            if not acc or acc.balance <= 0 or acc.status != AccountStatus.ACTIVE.value:
                return False, "Account is ineligible for interest accrual."

            rate = cls.DEFAULT_RATES.get(acc.account_type, Decimal("0.01"))
            accrued = (acc.balance * rate).quantize(Decimal("0.01"))

            if accrued <= 0:
                return False, "Interest calculated rounds to $0.00."

            acc.balance += accrued
            tx = Transaction(
                account_id=acc.id,
                type=TransactionType.INTEREST_CREDITED.value,
                amount=accrued,
                balance_after=acc.balance,
                description=f"Periodic interest accrued ({float(rate)*100:.2f}% p.a.)",
            )
            db.add(tx)
            AuditService.log(actor, "INTEREST_APPLIED", f"Accrued ${accrued:.2f} on {acc.account_number}")
            return True, f"Credited ${accrued:,.2f} in interest to account."

    @classmethod
    def apply_batch_interest(cls, actor: str) -> int:
        count = 0
        with get_db() as db:
            accounts = db.query(Account).filter(Account.status == AccountStatus.ACTIVE.value, Account.balance > 0).all()
            for acc in accounts:
                rate = cls.DEFAULT_RATES.get(acc.account_type, Decimal("0.01"))
                accrued = (acc.balance * rate).quantize(Decimal("0.01"))
                if accrued > 0:
                    acc.balance += accrued
                    tx = Transaction(
                        account_id=acc.id,
                        type=TransactionType.INTEREST_CREDITED.value,
                        amount=accrued,
                        balance_after=acc.balance,
                        description=f"Batch interest applied ({float(rate)*100:.2f}%)",
                    )
                    db.add(tx)
                    count += 1
            AuditService.log(actor, "BATCH_INTEREST", f"Interest posted across {count} accounts")
        return count