from uuid import uuid4

from database import Context
from models import Account, AccountStatus


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client_id: int, bank_id: int, branch: int, number: int) -> Account:
        account = Account(
            account_key=str(uuid4()),
            bank_id=bank_id,
            branch=branch,
            number=number,
            client_id=client_id,
            status=AccountStatus.PENDENTE,
        )
        self.session.add(account)
        return account

    def get_by_key(self, account_key: str) -> Account:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def get_by_identity(self, bank_id: int, branch: int, number: int) -> Account:
        return (
            self.session.query(Account)
            .filter(
                Account.bank_id == bank_id,
                Account.branch == branch,
                Account.number == number,
            )
            .first()
        )

    def count_open_by_client(self, client_id: int) -> int:
        return (
            self.session.query(Account)
            .filter(
                Account.client_id == client_id,
                Account.status != AccountStatus.DESATIVADA,
            )
            .count()
        )
