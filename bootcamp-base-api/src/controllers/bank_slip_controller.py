from datetime import date
from requests import RequestException
from requests.exceptions import Timeout
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from controllers.base_controller import BaseController
from connectors import BankSlipConnector
from dtos import BankSlipDTO, TransactionDTO
from errors import (
    AccountNotFound,
    BankSlipAlreadyPaid,
    BankSlipBeneficiaryMismatch,
    BankSlipExpired,
    BankSlipNotFound,
    BankSlipPaymentConflict,
    BankSlipRejected,
    BankSlipTimeout,
    IdempotencyKeyConflict,
    InsufficientBalance,
    InvalidSchema,
    SameAccountTransfer,
    SenderAccountNotActive,
    RecipientAccountNotAvailable,
)
from models import AccountStatus, BankSlipStatus, TransactionChannel, TransactionStatus
from repositories import AccountRepository, BankSlipRepository, TransactionRepository


class BankSlipController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.bank_slip_repository = BankSlipRepository(self.context)
        self.transaction_repository = TransactionRepository(self.context)

    def issue(self, payload: dict, raw_idempotency_key: str) -> tuple[dict, bool]:
        idempotency_key = self._parse_idempotency_key(raw_idempotency_key)
        expiration_date = self._parse_date(payload["data_vencimento"])
        if expiration_date <= date.today():
            raise BankSlipExpired()

        account = self.account_repository.get_by_key(payload["beneficiario"])
        if account is None:
            raise AccountNotFound(payload["beneficiario"])
        if account.status != AccountStatus.ATIVA:
            raise RecipientAccountNotAvailable()

        existing = self.bank_slip_repository.get_by_issuance_idempotency_key(idempotency_key)
        if existing is not None:
            self._ensure_same_issue(existing, account.id, payload, expiration_date)
            if existing.status == BankSlipStatus.REGISTRADO:
                return BankSlipDTO.obj_to_dict(existing), False
            return self._register(existing, account, payload, expiration_date, idempotency_key, False)

        bank_slip = self.bank_slip_repository.create(
            issuance_idempotency_key=idempotency_key,
            beneficiary_account_id=account.id,
            amount_cents=payload["valor"],
            expiration_date=expiration_date,
            payer_name=payload["pagador"]["nome"],
            payer_document_number=payload["pagador"]["documento"],
        )
        try:
            self.session.flush()
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.bank_slip_repository.get_by_issuance_idempotency_key(idempotency_key)
            if existing is None:
                raise
            self._ensure_same_issue(existing, account.id, payload, expiration_date)
            return BankSlipDTO.obj_to_dict(existing), False

        return self._register(bank_slip, account, payload, expiration_date, idempotency_key, True)

    def pay(self, bank_slip_key: str, payload: dict, raw_idempotency_key: str) -> tuple[dict, bool]:
        idempotency_key = self._parse_idempotency_key(raw_idempotency_key)
        payer = self.account_repository.get_by_key(payload["pagador"])
        if payer is None:
            raise AccountNotFound(payload["pagador"])
        if payer.status != AccountStatus.ATIVA:
            raise SenderAccountNotActive()

        existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            self._ensure_same_payment(existing, payer, bank_slip_key)
            if existing.status == TransactionStatus.EM_ANDAMENTO:
                return self._resume(existing, payer, False)
            return TransactionDTO.obj_to_dict(existing), False

        existing_for_boleto = self.transaction_repository.get_by_bank_slip_key(bank_slip_key)
        if existing_for_boleto is not None:
            if not self._same_payer(existing_for_boleto, payer):
                raise BankSlipPaymentConflict()
            if existing_for_boleto.status == TransactionStatus.EM_ANDAMENTO:
                return self._resume(existing_for_boleto, payer, False)
            raise BankSlipAlreadyPaid()

        connector = BankSlipConnector()
        bank_slip = self._external_request(connector.get_bank_slip_by_key, bank_slip_key)
        slip_data = self._validate_external_bank_slip(bank_slip_key, bank_slip)
        local_slip = self.bank_slip_repository.get_by_key(bank_slip_key)
        beneficiary = self._resolve_beneficiary(local_slip, slip_data)

        # The external lookup is complete. Lock only the short local
        # reservation section; _resume calls the mock after this commit.
        payer = self.account_repository.get_by_key_for_update(payload["pagador"])
        if payer is None:
            raise AccountNotFound(payload["pagador"])
        if payer.status != AccountStatus.ATIVA:
            raise SenderAccountNotActive()

        existing = self.transaction_repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            self.session.commit()
            self._ensure_same_payment(existing, payer, bank_slip_key)
            if existing.status == TransactionStatus.EM_ANDAMENTO:
                return self._resume(existing, payer, False)
            return TransactionDTO.obj_to_dict(existing), False

        existing_for_boleto = self.transaction_repository.get_by_bank_slip_key(bank_slip_key)
        if existing_for_boleto is not None:
            self.session.commit()
            if not self._same_payer(existing_for_boleto, payer):
                raise BankSlipPaymentConflict()
            if existing_for_boleto.status == TransactionStatus.EM_ANDAMENTO:
                return self._resume(existing_for_boleto, payer, False)
            raise BankSlipAlreadyPaid()

        if beneficiary is not None and beneficiary.id == payer.id:
            raise SameAccountTransfer()

        amount_cents = slip_data["amount"]
        pending_cents = self.transaction_repository.get_pending_outgoing_cents(self._endpoint(payer))
        if payer.balance_cents < pending_cents + amount_cents:
            raise InsufficientBalance()

        transaction = self.transaction_repository.create(
            idempotency_key=idempotency_key,
            sender_endpoint=self._endpoint(payer),
            recipient_endpoint=self._beneficiary_endpoint(slip_data, beneficiary),
            amount_cents=amount_cents,
            fee_cents=0,
            channel=TransactionChannel.BOLETO,
            status=TransactionStatus.EM_ANDAMENTO,
            bank_slip_key=bank_slip_key,
        )
        self.session.flush()
        self.session.commit()

        return self._resume(transaction, payer, True)

    def _register(self, account_slip, account, payload, expiration_date, idempotency_key, was_created):
        connector = BankSlipConnector()
        beneficiary_data = {
            "name": account.client.name,
            "document_number": account.client.document_number,
            "bank_code": account.bank_id,
            "branch": account.branch,
            "account": account.number,
        }
        response = self._external_request(
            connector.create_bank_slip,
            payload["valor"],
            expiration_date.isoformat(),
            payload["pagador"]["nome"],
            payload["pagador"]["documento"],
            beneficiary_data,
            idempotency_key,
        )
        if response.status not in (200, 201) or not isinstance(response.json, dict):
            account_slip.status = BankSlipStatus.FALHOU
            self.session.commit()
            raise BankSlipRejected()

        external_key = response.json.get("bank_slip_key")
        if not external_key:
            account_slip.status = BankSlipStatus.FALHOU
            self.session.commit()
            raise BankSlipRejected()

        account_slip.bank_slip_key = external_key
        account_slip.status = BankSlipStatus.REGISTRADO
        self.session.commit()
        return BankSlipDTO.obj_to_dict(account_slip), was_created

    def _resume(self, transaction, payer, was_created: bool):
        connector = BankSlipConnector()
        response = self._external_request(
            connector.get_bank_slip_by_key,
            transaction.bank_slip_key,
        )
        if response.status == 404:
            raise BankSlipNotFound(transaction.bank_slip_key)
        if response.status != 200 or not isinstance(response.json, dict):
            raise BankSlipRejected()

        if response.json.get("status") == "PAID":
            external_transaction_id = response.json.get("external_transaction_id")
            if not external_transaction_id:
                raise BankSlipRejected()
            self._persist_external_transaction_id(transaction, external_transaction_id)
            return self._settle(transaction.transaction_key, was_created)
        if response.json.get("status") == "EXPIRED":
            self._fail(transaction.transaction_key)
            raise BankSlipExpired()
        if response.json.get("status") != "OPEN":
            self._fail(transaction.transaction_key)
            raise BankSlipRejected()

        response = self._external_request(
            connector.pay_bank_slip,
            transaction.bank_slip_key,
            transaction.idempotency_key,
        )
        if response.status in (200, 201) and isinstance(response.json, dict):
            if response.json.get("status") == "SETTLED":
                external_transaction_id = response.json.get("external_transaction_id")
                if not external_transaction_id:
                    raise BankSlipRejected()
                self._persist_external_transaction_id(transaction, external_transaction_id)
                return self._settle(transaction.transaction_key, was_created)
        if response.status == 409:
            current = self._external_request(
                connector.get_bank_slip_by_key,
                transaction.bank_slip_key,
            )
            if (
                current.status == 200
                and isinstance(current.json, dict)
                and current.json.get("status") == "PAID"
            ):
                external_transaction_id = current.json.get("external_transaction_id")
                if not external_transaction_id:
                    raise BankSlipRejected()
                self._persist_external_transaction_id(transaction, external_transaction_id)
                return self._settle(transaction.transaction_key, was_created)
            self._fail(transaction.transaction_key)
            raise BankSlipPaymentConflict()
        self._fail(transaction.transaction_key)
        raise BankSlipRejected()

    def _persist_external_transaction_id(self, transaction, external_transaction_id: str) -> None:
        transaction.external_transaction_id = external_transaction_id
        self.session.commit()

    def _settle(self, transaction_key: str, was_created: bool):
        transaction = self.transaction_repository.get_by_transaction_key_for_update(transaction_key)
        if transaction.status != TransactionStatus.EM_ANDAMENTO:
            return TransactionDTO.obj_to_dict(transaction), False

        payer = self.account_repository.get_by_identity_for_update(
            transaction.sender_bank_id,
            transaction.sender_branch,
            transaction.sender_number,
        )
        local_slip = self.bank_slip_repository.get_by_key(transaction.bank_slip_key)
        beneficiary = None
        if local_slip is not None:
            beneficiary = self.account_repository.get_by_id_for_update(local_slip.beneficiary_account_id)
            if beneficiary is None or not self._same_endpoint(beneficiary, transaction):
                raise BankSlipBeneficiaryMismatch()
            if beneficiary.status not in (AccountStatus.ATIVA, AccountStatus.BLOQUEADA):
                raise BankSlipBeneficiaryMismatch()
            if beneficiary.id == payer.id:
                raise SameAccountTransfer()

        pending_cents = self.transaction_repository.get_pending_outgoing_cents(
            self._endpoint(payer), exclude_transaction_id=transaction.id
        )
        if payer.balance_cents < pending_cents + transaction.amount_cents:
            raise InsufficientBalance()

        payer.balance_cents -= transaction.amount_cents
        self.transaction_repository.add_entry(transaction.id, payer.id, -transaction.amount_cents)
        if beneficiary is not None:
            beneficiary.balance_cents += transaction.amount_cents
            self.transaction_repository.add_entry(transaction.id, beneficiary.id, transaction.amount_cents)
        transaction.status = TransactionStatus.CONCLUIDA
        self.session.commit()
        return TransactionDTO.obj_to_dict(transaction), was_created

    def _fail(self, transaction_key: str) -> None:
        transaction = self.transaction_repository.get_by_transaction_key_for_update(transaction_key)
        if transaction.status == TransactionStatus.EM_ANDAMENTO:
            transaction.status = TransactionStatus.FALHOU
            self.session.commit()

    @staticmethod
    def _external_request(function, *args):
        try:
            return function(*args)
        except (Timeout, RequestException):
            raise BankSlipTimeout()

    @staticmethod
    def _parse_idempotency_key(raw_key: str) -> str:
        try:
            return str(UUID(raw_key))
        except (AttributeError, ValueError):
            raise InvalidSchema("'chave_de_idempotencia' must be a UUID")

    @staticmethod
    def _parse_date(raw_date: str) -> date:
        try:
            return date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            raise InvalidSchema("'data_vencimento' must be an ISO date")

    @staticmethod
    def _ensure_same_issue(existing, account_id: int, payload: dict, expiration_date: date) -> None:
        if (
            existing.beneficiary_account_id != account_id
            or existing.amount_cents != payload["valor"]
            or existing.expiration_date != expiration_date
            or existing.payer_name != payload["pagador"]["nome"]
            or existing.payer_document_number != payload["pagador"]["documento"]
        ):
            raise IdempotencyKeyConflict()

    @staticmethod
    def _ensure_same_payment(existing, payer, bank_slip_key: str) -> None:
        if (
            existing.channel != TransactionChannel.BOLETO
            or existing.bank_slip_key != bank_slip_key
            or (existing.sender_bank_id, existing.sender_branch, existing.sender_number)
            != (payer.bank_id, payer.branch, payer.number)
        ):
            raise IdempotencyKeyConflict()

    @staticmethod
    def _same_payer(transaction, payer) -> bool:
        return (transaction.sender_bank_id, transaction.sender_branch, transaction.sender_number) == (
            payer.bank_id,
            payer.branch,
            payer.number,
        )

    def _validate_external_bank_slip(self, bank_slip_key: str, response) -> dict:
        if response.status == 404:
            raise BankSlipNotFound(bank_slip_key)
        if response.status != 200 or not isinstance(response.json, dict):
            raise BankSlipRejected()
        data = response.json
        if not isinstance(data.get("amount"), int) or data["amount"] <= 0:
            raise BankSlipRejected()
        if data.get("status") == "EXPIRED":
            raise BankSlipExpired()
        if data.get("status") == "PAID":
            raise BankSlipAlreadyPaid()
        if data.get("status") != "OPEN":
            raise BankSlipRejected()
        expiration_date = self._parse_date(data.get("expiration_date"))
        if expiration_date < date.today():
            raise BankSlipExpired()
        if not isinstance(data.get("beneficiary_data"), dict):
            raise BankSlipRejected()
        return data

    def _resolve_beneficiary(self, local_slip, slip_data):
        if local_slip is None:
            return None
        beneficiary = self.account_repository.get_by_id(local_slip.beneficiary_account_id)
        if beneficiary is None or not self._matches_external_beneficiary(beneficiary, slip_data["beneficiary_data"]):
            raise BankSlipBeneficiaryMismatch()
        if local_slip.amount_cents != slip_data["amount"]:
            raise BankSlipRejected()
        return beneficiary

    @staticmethod
    def _matches_external_beneficiary(account, beneficiary_data: dict) -> bool:
        return (
            beneficiary_data.get("bank_code") == account.bank_id
            and beneficiary_data.get("branch") == account.branch
            and beneficiary_data.get("account") == account.number
        )

    @staticmethod
    def _beneficiary_endpoint(slip_data: dict, beneficiary) -> dict:
        if beneficiary is not None:
            return {
                "bank_id": beneficiary.bank_id,
                "branch": beneficiary.branch,
                "number": beneficiary.number,
            }
        data = slip_data["beneficiary_data"]
        return {
            "bank_id": data["bank_code"],
            "branch": data["branch"],
            "number": data["account"],
        }

    @staticmethod
    def _same_endpoint(account, transaction) -> bool:
        return (
            account.bank_id == transaction.recipient_bank_id
            and account.branch == transaction.recipient_branch
            and account.number == transaction.recipient_number
        )

    @staticmethod
    def _endpoint(account) -> dict:
        return {"bank_id": account.bank_id, "branch": account.branch, "number": account.number}
