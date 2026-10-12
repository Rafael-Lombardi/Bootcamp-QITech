from models import Account


class AccountDTO:
    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        return {
            "chave_conta": account.account_key,
            "banco_id": account.bank_id,
            "agencia": account.branch,
            "numero": account.number,
            "estado": account.status.value,
            "saldo": f"{account.balance:.2f}",
        }

    @staticmethod
    def only_key(account: Account) -> dict:
        return {"chave_conta": account.account_key}
