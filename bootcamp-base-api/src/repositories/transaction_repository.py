from uuid import uuid4

from database import Context
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

    def create(
        self,
        idempotency_key: str,
        sender_account_id: int,
        recipient_account_id: int,
        amount_cents: int,
        fee_cents: int,
        channel: TransactionChannel,
    ) -> Transaction:
        transaction = Transaction(
            transaction_key=str(uuid4()),
            idempotency_key=idempotency_key,
            sender_account_id=sender_account_id,
            recipient_account_id=recipient_account_id,
            amount_cents=amount_cents,
            fee_cents=fee_cents,
            channel=channel,
            status=TransactionStatus.CONCLUIDA,
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
