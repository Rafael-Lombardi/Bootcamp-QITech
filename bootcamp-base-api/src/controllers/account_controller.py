from sqlalchemy.exc import IntegrityError

from constants import BANK_ID
from controllers.base_controller import BaseController
from dtos import AccountDTO
from errors import AccountNotFound, AccountOwnedByAnotherClient, ClientAccountLimit, ClientNotFound
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

    @staticmethod
    def _existing_account_response(
        account, client_id: int, branch: int, number: int
    ) -> tuple[dict, bool]:
        if account.client_id != client_id:
            raise AccountOwnedByAnotherClient(branch, number)
        return AccountDTO.only_key(account), False
