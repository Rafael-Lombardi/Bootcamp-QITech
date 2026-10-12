from uuid import uuid4

from database import Context
from sqlalchemy import and_, or_

from models import Account, AccountStatus, AccountStatusEvent, Transaction, TransactionStatus


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

    def get_by_key_for_update(self, account_key: str) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.account_key == account_key)
            .populate_existing()
            .with_for_update()
            .first()
        )

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

    def get_by_identity_for_update(self, bank_id: int, branch: int, number: int) -> Account:
        return (
            self.session.query(Account)
            .filter(
                Account.bank_id == bank_id,
                Account.branch == branch,
                Account.number == number,
            )
            .populate_existing()
            .with_for_update()
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

    def get_pair_for_update(self, first_id: int, second_id: int) -> list[Account]:
        return (
            self.session.query(Account)
            .filter(Account.id.in_((first_id, second_id)))
            .order_by(Account.id)
            .populate_existing()
            .with_for_update()
            .all()
        )

    def has_in_progress_transaction(self, account: Account) -> bool:
        sender = and_(
            Transaction.sender_bank_id == account.bank_id,
            Transaction.sender_branch == account.branch,
            Transaction.sender_number == account.number,
        )
        recipient = and_(
            Transaction.recipient_bank_id == account.bank_id,
            Transaction.recipient_branch == account.branch,
            Transaction.recipient_number == account.number,
        )
        return (
            self.session.query(Transaction.id)
            .filter(Transaction.status == TransactionStatus.EM_ANDAMENTO)
            .filter(or_(sender, recipient))
            .first()
            is not None
        )

    def create_status_event(self, account_id: int, status: AccountStatus, reason: str) -> AccountStatusEvent:
        event = AccountStatusEvent(account_id=account_id, status=status, reason=reason)
        self.session.add(event)
        return event
