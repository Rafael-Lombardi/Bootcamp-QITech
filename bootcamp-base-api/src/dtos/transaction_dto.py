from models import Transaction


class TransactionDTO:
    @staticmethod
    def obj_to_dict(transaction: Transaction) -> dict:
        return {
            "chave_transacao": transaction.transaction_key,
            "estado": transaction.status.value,
            "valor": transaction.amount_cents,
            "tarifa_cobrada": transaction.fee_cents,
        }
