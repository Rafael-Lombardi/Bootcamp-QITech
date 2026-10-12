from sqlalchemy.exc import IntegrityError

from constants import BANK_ID
from controllers.base_controller import BaseController
from dtos import AccountDTO
from errors import (
    AccountHasBalance,
    AccountHasInProgressTransaction,
    AccountNotFound,
    AccountOwnedByAnotherClient,
    ClientAccountLimit,
    ClientNotFound,
)
from models import AccountStatus
from repositories import AccountRepository, ClientRepository


MAX_OPEN_ACCOUNTS = 5


class AccountController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)
        self.client_repository = ClientRepository(self.context)

    def create(self, client_key: str, account_data: dict) -> tuple[dict, bool]:
        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise ClientNotFound(client_key)

        branch = account_data["agencia"]
        number = account_data["numero"]
        existing_account = self.account_repository.get_by_identity(BANK_ID, branch, number)
        if existing_account is not None:
            return self._existing_account_response(existing_account, client.id, branch, number)

        if self.account_repository.count_open_by_client(client.id) >= MAX_OPEN_ACCOUNTS:
            raise ClientAccountLimit(MAX_OPEN_ACCOUNTS)

        account = self.account_repository.create(client.id, BANK_ID, branch, number)
        try:
            self.session.flush()
            account_dto = AccountDTO.only_key(account)
            self.session.commit()
            return account_dto, True
        except IntegrityError:
            self.session.rollback()
            existing_account = self.account_repository.get_by_identity(BANK_ID, branch, number)
            if existing_account is None:
                raise
            return self._existing_account_response(existing_account, client.id, branch, number)

    def get_by_key(self, account_key: str) -> dict:
        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise AccountNotFound(account_key)
        return AccountDTO.obj_to_dict(account)

    def update_status(self, account_key: str, account_data: dict) -> dict:
        account = self.account_repository.get_by_key_for_update(account_key)
        if account is None:
            raise AccountNotFound(account_key)

        new_status = AccountStatus(account_data["novo_estado"])
        if new_status == AccountStatus.DESATIVADA:
            if account.balance_cents != 0:
                raise AccountHasBalance()
            if self.account_repository.has_in_progress_transaction(account):
                raise AccountHasInProgressTransaction()

        account.status = new_status
        self.account_repository.create_status_event(account.id, new_status, account_data["razao"])
        self.session.commit()
        return AccountDTO.obj_to_dict(account)

    @staticmethod
    def _existing_account_response(
        account, client_id: int, branch: int, number: int
    ) -> tuple[dict, bool]:
        if account.client_id != client_id:
            raise AccountOwnedByAnotherClient(branch, number)
        return AccountDTO.only_key(account), False
