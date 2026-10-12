from database import Context
from models import BankSlip, BankSlipStatus


class BankSlipRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_issuance_idempotency_key(self, idempotency_key: str) -> BankSlip:
        return (
            self.session.query(BankSlip)
            .filter(BankSlip.issuance_idempotency_key == idempotency_key)
            .first()
        )

    def get_by_key(self, bank_slip_key: str) -> BankSlip:
        return (
            self.session.query(BankSlip)
            .filter(BankSlip.bank_slip_key == bank_slip_key)
            .first()
        )

    def create(
        self,
        issuance_idempotency_key: str,
        beneficiary_account_id: int,
        amount_cents: int,
        expiration_date,
        payer_name: str,
        payer_document_number: str,
    ) -> BankSlip:
        bank_slip = BankSlip(
            issuance_idempotency_key=issuance_idempotency_key,
            beneficiary_account_id=beneficiary_account_id,
            amount_cents=amount_cents,
            expiration_date=expiration_date,
            payer_name=payer_name,
            payer_document_number=payer_document_number,
            status=BankSlipStatus.EM_ANDAMENTO,
        )
        self.session.add(bank_slip)
        return bank_slip
