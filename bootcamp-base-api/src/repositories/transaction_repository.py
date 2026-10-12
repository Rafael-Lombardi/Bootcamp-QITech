from uuid import uuid4

from database import Context
from sqlalchemy import func
from models import LedgerEntry, Transaction, TransactionChannel, TransactionStatus


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_idempotency_key(self, idempotency_key: str) -> Transaction:
        return (
            self.session.query(Transaction)
            .filter(Transaction.idempotency_key == idempotency_key)
            .first()
        )

    def get_by_transaction_key_for_update(self, transaction_key: str) -> Transaction:
        return (
            self.session.query(Transaction)
            .filter(Transaction.transaction_key == transaction_key)
            .populate_existing()
            .with_for_update()
            .first()
        )

    def get_by_bank_slip_key(self, bank_slip_key: str) -> Transaction:
        return (
            self.session.query(Transaction)
            .filter(Transaction.bank_slip_key == bank_slip_key)
            .first()
        )

    def get_pending_outgoing_cents(
        self,
        sender_endpoint: dict,
        exclude_transaction_id: int = None,
    ) -> int:
        query = (
            self.session.query(
                func.coalesce(func.sum(Transaction.amount_cents + Transaction.fee_cents), 0)
            )
            .filter(
                Transaction.sender_bank_id == sender_endpoint["bank_id"],
                Transaction.sender_branch == sender_endpoint["branch"],
                Transaction.sender_number == sender_endpoint["number"],
                Transaction.status == TransactionStatus.EM_ANDAMENTO,
            )
        )
        if exclude_transaction_id is not None:
            query = query.filter(Transaction.id != exclude_transaction_id)
        return int(query.scalar() or 0)

    def create(
        self,
        idempotency_key: str,
        sender_endpoint: dict,
        recipient_endpoint: dict,
        amount_cents: int,
        fee_cents: int,
        channel: TransactionChannel,
        status: TransactionStatus = TransactionStatus.CONCLUIDA,
        bank_slip_key: str = None,
    ) -> Transaction:
        transaction_key = str(uuid4())
        transaction = Transaction(
            transaction_key=transaction_key,
            idempotency_key=idempotency_key,
            sender_bank_id=sender_endpoint["bank_id"],
            sender_branch=sender_endpoint["branch"],
            sender_number=sender_endpoint["number"],
            recipient_bank_id=recipient_endpoint["bank_id"],
            recipient_branch=recipient_endpoint["branch"],
            recipient_number=recipient_endpoint["number"],
            amount_cents=amount_cents,
            fee_cents=fee_cents,
            channel=channel,
            status=status,
            bank_slip_key=bank_slip_key,
        )
        self.session.add(transaction)
        return transaction

    def add_entry(self, transaction_id: int, account_id: int, movement_cents: int) -> LedgerEntry:
        entry = LedgerEntry(
            transaction_id=transaction_id,
            account_id=account_id,
            movement_cents=movement_cents,
        )
        self.session.add(entry)
        return entry
