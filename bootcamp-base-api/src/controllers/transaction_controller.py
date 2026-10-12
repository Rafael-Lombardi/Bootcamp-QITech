from uuid import UUID

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from dtos import TransactionDTO
from errors import (
    IdempotencyKeyConflict,
    InsufficientBalance,
    InvalidSchema,
    RecipientAccountNotAvailable,
    RecipientAccountNotFound,
    SameAccountTransfer,
    SenderAccountNotActive,
    SenderAccountNotFound,
)
from models import AccountStatus, ClientType, TransactionChannel
from repositories import AccountRepository, TransactionRepository


class TransactionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)

    def create(self, payload: dict, raw_idempotency_key: str) -> tuple[dict, bool]:
        idempotency_key = self._parse_idempotency_key(raw_idempotency_key)
        channel = TransactionChannel(payload["canal"])
        amount_cents = payload["valor"]

        sender = self.account_repository.get_by_key(payload["remetente"])
        if sender is None:
            raise SenderAccountNotFound(payload["remetente"])

        recipient_data = payload["destinatario"]
        recipient = self.account_repository.get_by_identity(
            recipient_data["banco_id"],
            recipient_data["agencia"],
            recipient_data["conta"],
        )
        if recipient is None:
            raise RecipientAccountNotFound(
                recipient_data["banco_id"],
                recipient_data["agencia"],
                recipient_data["conta"],
            )

        if sender.id == recipient.id:
            raise SameAccountTransfer()

        existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            if self._same_request(existing, sender.id, recipient.id, amount_cents, channel):
                return TransactionDTO.obj_to_dict(existing), False
            raise IdempotencyKeyConflict()

        locked_accounts = self.account_repository.get_pair_for_update(sender.id, recipient.id)
        locked_by_id = {account.id: account for account in locked_accounts}
        sender = locked_by_id[sender.id]
        recipient = locked_by_id[recipient.id]

        if sender.status != AccountStatus.ATIVA:
            raise SenderAccountNotActive()
        if recipient.status not in (AccountStatus.ATIVA, AccountStatus.BLOQUEADA):
            raise RecipientAccountNotAvailable()

        fee_cents = self._calculate_fee(sender.client.client_type, channel, amount_cents)
        if sender.balance_cents < amount_cents + fee_cents:
            raise InsufficientBalance()

        transaction = self.transaction_repository.create(
            idempotency_key=idempotency_key,
            sender_account_id=sender.id,
            recipient_account_id=recipient.id,
            amount_cents=amount_cents,
            fee_cents=fee_cents,
            channel=channel,
        )
        sender.balance_cents -= amount_cents + fee_cents
        recipient.balance_cents += amount_cents
        try:
            self.session.flush()
            self.transaction_repository.add_entry(transaction.id, sender.id, -(amount_cents + fee_cents))
            self.transaction_repository.add_entry(transaction.id, recipient.id, amount_cents)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            if self._same_request(existing, sender.id, recipient.id, amount_cents, channel):
                return TransactionDTO.obj_to_dict(existing), False
            raise IdempotencyKeyConflict()

        return TransactionDTO.obj_to_dict(transaction), True

    @staticmethod
    def _parse_idempotency_key(raw_key: str) -> str:
        try:
            return str(UUID(raw_key))
        except (AttributeError, ValueError):
            raise InvalidSchema("'chave_de_idempotencia' must be a UUID")

    @staticmethod
    def _calculate_fee(client_type: ClientType, channel: TransactionChannel, amount_cents: int) -> int:
        if channel == TransactionChannel.TED:
            return 1000
        if client_type == ClientType.PF:
            return 0
        return min((amount_cents * 5 + 500) // 1000, 1000)

    @staticmethod
    def _same_request(transaction, sender_id: int, recipient_id: int, amount_cents: int, channel) -> bool:
        return (
            transaction.sender_account_id == sender_id
            and transaction.recipient_account_id == recipient_id
            and transaction.amount_cents == amount_cents
            and transaction.channel == channel
        )
