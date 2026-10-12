from uuid import UUID

from requests import RequestException
from requests.exceptions import Timeout
from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from connectors import ExternalBankConnector
from constants import BANK_ID
from dtos import TransactionDTO
from errors import (
    ExternalBankTimeout,
    ExternalRecipientNotAvailable,
    ExternalRecipientNotFound,
    ExternalTransactionRejected,
    IdempotencyKeyConflict,
    InsufficientBalance,
    InvalidSchema,
    RecipientAccountNotAvailable,
    RecipientAccountNotFound,
    SameAccountTransfer,
    SenderAccountNotActive,
    SenderAccountNotFound,
)
from models import AccountStatus, ClientType, TransactionChannel, TransactionStatus
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
        if recipient_data["banco_id"] != BANK_ID:
            existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                self._ensure_same_request(existing, sender, recipient_data, amount_cents, channel)
                if existing.status == TransactionStatus.EM_ANDAMENTO:
                    return self._resume_external(existing, sender, recipient_data, channel)
                if existing.status == TransactionStatus.FALHOU and recipient_data["banco_id"] != BANK_ID:
                    raise ExternalTransactionRejected()
                return TransactionDTO.obj_to_dict(existing), False
            return self._create_external(
                sender,
                recipient_data,
                amount_cents,
                channel,
                idempotency_key,
            )

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
            if self._same_request(existing, self._endpoint(sender), self._endpoint(recipient), amount_cents, channel):
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
        pending_cents = self.transaction_repository.get_pending_outgoing_cents(self._endpoint(sender))
        if sender.balance_cents < pending_cents + amount_cents + fee_cents:
            raise InsufficientBalance()

        transaction = self.transaction_repository.create(
            idempotency_key=idempotency_key,
            sender_endpoint=self._endpoint(sender),
            recipient_endpoint=self._endpoint(recipient),
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
            if self._same_request(existing, self._endpoint(sender), self._endpoint(recipient), amount_cents, channel):
                return TransactionDTO.obj_to_dict(existing), False
            raise IdempotencyKeyConflict()

        return TransactionDTO.obj_to_dict(transaction), True

    def _create_external(
        self,
        sender,
        recipient_data: dict,
        amount_cents: int,
        channel: TransactionChannel,
        idempotency_key: str,
    ) -> tuple[dict, bool]:
        self._validate_sender(sender)
        connector = ExternalBankConnector()
        self._validate_external_recipient(connector, recipient_data)

        sender = self.account_repository.get_by_key_for_update(sender.account_key)
        if sender is None:
            raise SenderAccountNotFound("sender")

        existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            self.session.commit()
            self._ensure_same_request(existing, sender, recipient_data, amount_cents, channel)
            if existing.status == TransactionStatus.EM_ANDAMENTO:
                return self._resume_external(existing, sender, recipient_data, channel)
            return TransactionDTO.obj_to_dict(existing), False

        self._validate_sender(sender)
        fee_cents = self._calculate_fee(sender.client.client_type, channel, amount_cents)
        sender_endpoint = self._endpoint(sender)
        pending_cents = self.transaction_repository.get_pending_outgoing_cents(sender_endpoint)
        if sender.balance_cents < pending_cents + amount_cents + fee_cents:
            raise InsufficientBalance()

        transaction = self.transaction_repository.create(
            idempotency_key=idempotency_key,
            sender_endpoint=sender_endpoint,
            recipient_endpoint=self._endpoint_from_data(recipient_data),
            amount_cents=amount_cents,
            fee_cents=fee_cents,
            channel=channel,
            status=TransactionStatus.EM_ANDAMENTO,
        )
        transaction.external_transaction_id = transaction.transaction_key
        self.session.flush()
        self.session.commit()

        response = self._external_request(
            connector.create_transaction,
            transaction.external_transaction_id,
            amount_cents,
            channel.value,
            sender_endpoint,
            self._endpoint_from_data(recipient_data),
        )
        return self._apply_external_response(transaction.transaction_key, response, True)

    def _resume_external(
        self,
        transaction,
        sender,
        recipient_data: dict,
        channel: TransactionChannel,
    ) -> tuple[dict, bool]:
        connector = ExternalBankConnector()
        response = self._external_request(
            connector.get_transaction,
            transaction.external_transaction_id,
        )
        if response.status == 404:
            response = self._external_request(
                connector.create_transaction,
                transaction.external_transaction_id,
                transaction.amount_cents,
                channel.value,
                self._endpoint(sender),
                self._endpoint_from_data(recipient_data),
            )
        return self._apply_external_response(transaction.transaction_key, response, False)

    def _validate_external_recipient(self, connector: ExternalBankConnector, recipient_data: dict) -> None:
        response = self._external_request(
            connector.get_account,
            recipient_data["banco_id"],
            recipient_data["agencia"],
            recipient_data["conta"],
        )
        if response.status == 404:
            raise ExternalRecipientNotFound(
                recipient_data["banco_id"],
                recipient_data["agencia"],
                recipient_data["conta"],
            )
        if response.status != 200 or not isinstance(response.json, dict):
            raise ExternalRecipientNotFound(
                recipient_data["banco_id"],
                recipient_data["agencia"],
                recipient_data["conta"],
            )
        if response.json.get("status") != "ACTIVE":
            raise ExternalRecipientNotAvailable(
                recipient_data["banco_id"],
                recipient_data["agencia"],
                recipient_data["conta"],
            )

    @staticmethod
    def _external_request(function, *args):
        try:
            return function(*args)
        except (Timeout, RequestException):
            raise ExternalBankTimeout()

    def _apply_external_response(
        self,
        transaction_key: str,
        response,
        was_created: bool,
    ) -> tuple[dict, bool]:
        if response.status not in (200, 201) or not isinstance(response.json, dict):
            raise ExternalTransactionRejected()
        if response.json.get("status") == "SETTLED":
            return self._settle_external(transaction_key, was_created)
        if response.json.get("status") == "REJECTED":
            self._fail_external(transaction_key)
            raise ExternalTransactionRejected()
        raise ExternalTransactionRejected()

    def _settle_external(self, transaction_key: str, was_created: bool) -> tuple[dict, bool]:
        transaction = self.transaction_repository.get_by_transaction_key_for_update(transaction_key)
        if transaction.status != TransactionStatus.EM_ANDAMENTO:
            return TransactionDTO.obj_to_dict(transaction), False

        sender = self.account_repository.get_by_identity_for_update(
            transaction.sender_bank_id,
            transaction.sender_branch,
            transaction.sender_number,
        )
        pending_cents = self.transaction_repository.get_pending_outgoing_cents(
            self._endpoint(sender),
            exclude_transaction_id=transaction.id,
        )
        if sender.balance_cents < pending_cents + transaction.amount_cents + transaction.fee_cents:
            raise InsufficientBalance()

        sender.balance_cents -= transaction.amount_cents + transaction.fee_cents
        transaction.status = TransactionStatus.CONCLUIDA
        self.transaction_repository.add_entry(
            transaction.id,
            sender.id,
            -(transaction.amount_cents + transaction.fee_cents),
        )
        self.session.commit()
        return TransactionDTO.obj_to_dict(transaction), was_created

    def _fail_external(self, transaction_key: str) -> None:
        transaction = self.transaction_repository.get_by_transaction_key_for_update(transaction_key)
        if transaction.status == TransactionStatus.EM_ANDAMENTO:
            transaction.status = TransactionStatus.FALHOU
            self.session.commit()

    @staticmethod
    def _validate_sender(sender) -> None:
        if sender.status != AccountStatus.ATIVA:
            raise SenderAccountNotActive()

    def _ensure_same_request(
        self,
        transaction,
        sender,
        recipient_data: dict,
        amount_cents: int,
        channel: TransactionChannel,
    ) -> None:
        if not self._same_request(
            transaction,
            self._endpoint(sender),
            self._endpoint_from_data(recipient_data),
            amount_cents,
            channel,
        ):
            raise IdempotencyKeyConflict()

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
    def _same_request(transaction, sender_endpoint: dict, recipient_endpoint: dict, amount_cents: int, channel) -> bool:
        return (
            (transaction.sender_bank_id, transaction.sender_branch, transaction.sender_number)
            == (sender_endpoint["bank_id"], sender_endpoint["branch"], sender_endpoint["number"])
            and (transaction.recipient_bank_id, transaction.recipient_branch, transaction.recipient_number)
            == (recipient_endpoint["bank_id"], recipient_endpoint["branch"], recipient_endpoint["number"])
            and transaction.amount_cents == amount_cents
            and transaction.channel == channel
        )

    @staticmethod
    def _endpoint(account) -> dict:
        return {
            "bank_id": account.bank_id,
            "branch": account.branch,
            "number": account.number,
        }

    @staticmethod
    def _endpoint_from_data(account: dict) -> dict:
        return {
            "bank_id": account["banco_id"],
            "branch": account["agencia"],
            "number": account["conta"],
        }
