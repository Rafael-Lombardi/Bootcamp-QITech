from models import BankSlip


class BankSlipDTO:
    @staticmethod
    def obj_to_dict(bank_slip: BankSlip) -> dict:
        return {
            "chave_boleto": bank_slip.bank_slip_key,
            "valor": bank_slip.amount_cents,
            "data_vencimento": bank_slip.expiration_date.isoformat(),
            "estado": bank_slip.status.value,
        }
