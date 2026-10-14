"""Core ledger operations guaranteeing atomic balances."""

from decimal import Decimal
from typing import List, Optional, Tuple
import uuid
from database.connection import get_db
from models.account import Account, AccountStatus, AccountType
from models.transaction import Transaction, TransactionType
from security.crypto import CryptoManager
from services.audit_service import AuditService


class BankingService:
    @staticmethod
    def create_account(
        user_id: str, account_type: str, initial_deposit: float = 0.0
    ) -> Tuple[bool, str, Optional[str]]:
        if initial_deposit < 0:
            return False, "Initial deposit cannot be negative.", None

        with get_db() as db:
            acc_number = CryptoManager.generate_account_number()
            account = Account(
                account_number=acc_number,
                user_id=user_id,
                account_type=account_type,
                balance=Decimal(str(round(initial_deposit, 2))),
                status=AccountStatus.ACTIVE.value,
            )
            db.add(account)
            db.flush()

            if initial_deposit > 0:
                tx = Transaction(
                    account_id=account.id,
                    type=TransactionType.DEPOSIT.value,
                    amount=Decimal(str(round(initial_deposit, 2))),
                    balance_after=account.balance,
                    description="Initial opening deposit",
                )
                db.add(tx)

            AuditService.log(user_id, "ACCOUNT_CREATED", f"Account #{acc_number} ({account_type}) opened")
            return True, "Account created successfully.", acc_number

    @staticmethod
    def deposit(account_id: str, amount: float, actor: str) -> Tuple[bool, str]:
        if amount <= 0:
            return False, "Deposit amount must be strictly positive."

        with get_db() as db:
            acc = db.query(Account).filter(Account.id == account_id).with_for_update().first()
            if not acc or acc.is_deleted:
                return False, "Account record not found."
            if acc.status != AccountStatus.ACTIVE.value:
                return False, f"Account is {acc.status.lower()} and cannot receive deposits."

            dec_amount = Decimal(str(round(amount, 2)))
            acc.balance += dec_amount

            tx = Transaction(
                account_id=acc.id,
                type=TransactionType.DEPOSIT.value,
                amount=dec_amount,
                balance_after=acc.balance,
                description="Cash / Electronic Deposit",
            )
            db.add(tx)
            AuditService.log(actor, "DEPOSIT", f"${amount:.2f} credited to {acc.account_number}")
            return True, f"Successfully deposited ${amount:,.2f}."

    @staticmethod
    def withdraw(account_id: str, amount: float, actor: str) -> Tuple[bool, str]:
        if amount <= 0:
            return False, "Withdrawal amount must be strictly positive."

        with get_db() as db:
            acc = db.query(Account).filter(Account.id == account_id).with_for_update().first()
            if not acc or acc.is_deleted:
                return False, "Account record not found."
            if acc.status != AccountStatus.ACTIVE.value:
                return False, f"Account is {acc.status.lower()}."

            dec_amount = Decimal(str(round(amount, 2)))
            available = acc.available_balance

            if float(dec_amount) > available:
                return False, f"Insufficient funds. Maximum available: ${available:,.2f}"

            acc.balance -= dec_amount
            tx = Transaction(
                account_id=acc.id,
                type=TransactionType.WITHDRAWAL.value,
                amount=dec_amount,
                balance_after=acc.balance,
                description="Cash / Terminal Withdrawal",
            )
            db.add(tx)

            # Apply overdraft fee if balance dips negative
            if acc.balance < 0:
                fee = Decimal("25.00")
                acc.balance -= fee
                fee_tx = Transaction(
                    account_id=acc.id,
                    type=TransactionType.FEE_CHARGED.value,
                    amount=fee,
                    balance_after=acc.balance,
                    description="Overdraft protection fee",
                )
                db.add(fee_tx)

            AuditService.log(actor, "WITHDRAWAL", f"${amount:.2f} debited from {acc.account_number}")
            return True, f"Successfully withdrew ${amount:,.2f}."

    @staticmethod
    def transfer(source_account_id: str, dest_account_number: str, amount: float, actor: str) -> Tuple[bool, str]:
        if amount <= 0:
            return False, "Transfer sum must be greater than zero."

        with get_db() as db:
            src = db.query(Account).filter(Account.id == source_account_id).with_for_update().first()
            dst = (
                db.query(Account)
                .filter(Account.account_number == dest_account_number.strip())
                .with_for_update()
                .first()
            )

            if not src:
                return False, "Originating account not found."
            if not dst:
                return False, "Destination account does not exist."
            if src.id == dst.id:
                return False, "Sender and receiver accounts must be distinct."
            if src.status != AccountStatus.ACTIVE.value or dst.status != AccountStatus.ACTIVE.value:
                return False, "Both accounts must be Active to clear transfers."

            dec_amount = Decimal(str(round(amount, 2)))
            if float(dec_amount) > src.available_balance:
                return False, "Insufficient available balance to fund this transfer."

            reference_pair = str(uuid.uuid4())
            src.balance -= dec_amount
            dst.balance += dec_amount

            # Outgoing leg
            tx_out = Transaction(
                account_id=src.id,
                type=TransactionType.TRANSFER_SENT.value,
                amount=dec_amount,
                balance_after=src.balance,
                description=f"Transfer to #{dst.account_number} ({dst.owner.full_name})",
                related_account_number=dst.account_number,
                reference_id=reference_pair,
            )
            # Incoming leg
            tx_in = Transaction(
                account_id=dst.id,
                type=TransactionType.TRANSFER_RECEIVED.value,
                amount=dec_amount,
                balance_after=dst.balance,
                description=f"Transfer from #{src.account_number} ({src.owner.full_name})",
                related_account_number=src.account_number,
                reference_id=reference_pair,
            )
            db.add_all([tx_out, tx_in])
            AuditService.log(
                actor, "TRANSFER", f"${amount:.2f} transferred from {src.account_number} to {dst.account_number}"
            )
            return True, f"Successfully transferred ${amount:,.2f} to {dst.owner.full_name}."